# -*- coding: utf-8 -*-
"""
parse_intensity_log.py

Dev/analysis tool -- not part of the installed fus_driving_systems package (same category as
check_duplication.py). Reads any FDS log file containing lines produced by IGT's
ExecListener.onPulseResult() (fus_driving_systems/igt/utils.py) and extracts per-channel
measurements (V/Vfwd, I, PhaseV/I, PhaseV/Vref, Freq, Pow) per pulse -- works against an older,
single combined log file just as well as the newer split-out log_measurements_*.txt file (see
logging_config.initialize_logger()): this script only looks for the onPulseResult lines
themselves, wherever they live in the given file.

It also looks for the configured/expected voltage and amplitude each transducer slot was
actually sent with -- the "Voltage [V]: [...]"/"Amplitude [%]: [...]" pair inside each slot's
own "...with the following parameters is validated before sending:" block (TUSProtocol/
Sequence's __str__()) -- and compares those against the *measured* per-channel voltage from
onPulseResult: both the percentage difference from the configured value, and the variability
(std/coefficient of variation) within the measurements themselves.

Multi-slot simultaneous sends (e.g. an older two_transducers_simultaneous-style log, where each
transducer is logged as its own "Sequence") are handled by assigning each slot a channel range,
in the order the slots were configured, sized by each one's own "Transducer elements: N" --
slot 1 gets channels [0, N1), slot 2 gets [N1, N1+N2), and so on. This is NOT the same thing as
the "Sequence number/buffer (for IGT purposes)" label on each slot's own block -- that label is
just this old logging format's own per-slot identifier, not a real hardware buffer, and does NOT
correspond to the physical channel it drives. The actual hardware buffer/execution grouping
comes from "Listener: EXEC START (buff: N, ...)" lines (utils.py's ExecListener.
onSequenceStart()): every slot configured since the previous EXEC START (or since the start of
the file) is treated as belonging to that one execution, in channel order.

Usage:
    Edit the constants right below these imports (LOGFILE, OUTPUT_PREFIX, N_EXTREMES), then just
    hit Run -- no command-line arguments to set up, so this also runs straight from PyCharm's
    Run button with no Run Configuration needed. Set LOG_DIR instead of LOGFILE to process every
    log file in a folder in one run (see LOG_DIR's own comment).

Output (always printed to stdout):
    - Every execution found, and the slot(s) (transducer/channel range/configured voltage and
      amplitude) that were part of it.
    - Per-channel summary: measurement count, mean/std voltage, coefficient of variation,
      percentage difference from that channel's own configured voltage, and min/max voltage
      (mean/std alone can hide an occasional large excursion -- min/max show the actual swing
      directly).
    - The N lowest/highest individual pulses per channel (N_EXTREMES, default 5, 0 disables
      this), with their exec index/timestamp -- pins an observed excursion down to specific
      pulses instead of only knowing the overall min/max exists somewhere in the run.

Output files:
    <prefix>_voltage.png               -> voltage per channel over time, with the SIGNED
                                           percentage-deviation-over-time view right below it
                                           (same time axis) so the two are always read together,
                                           a color-coded per-channel summary table (mean/CV%/min/
                                           max/swing(V)/swing%/expected/%diff/mean|%dev|/
                                           mean|dev|(V), see summarize_channels()), and a title
                                           naming what was configured -- self-contained
"""

import re
from pathlib import Path

import pandas as pd

# Edit these, then just hit Run -- no command-line arguments needed.
LOGFILE = str(Path(r"C:\path\to\your\logs\intensity_log_2026-08-25_11-57-11_standalone_igt.txt"))
# Set this to a folder to process every log file in it in one run instead of just LOGFILE --
# LOGFILE/OUTPUT_PREFIX are then ignored; each file gets its own <its own stem>_voltage.png
# written next to it, and a file with no onPulseResult lines at all (e.g. a native IGT log, or
# something unrelated) is skipped with a message rather than aborting the whole run. Not
# recursive -- only files directly inside this folder are processed.
LOG_DIR = None
# output filename prefix; None uses LOGFILE's own name (ignored under LOG_DIR, see its comment)
OUTPUT_PREFIX = None
N_EXTREMES = 5  # how many lowest/highest pulses to list per channel; 0 disables that section

# Example lines (note: the file uses a degree sign that isn't always valid UTF-8, so it's read
# with cp1252 encoding, falling back to latin-1 if that fails -- matches logging_config.py's
# FileHandler, which doesn't specify an encoding and so uses the platform default, typically
# cp1252 on Windows):
#
# 2026-08-25 11:57:12,856 - DEBUG - igt_ds - send_sequence line 310 Sequence with the following
#   parameters is validated before sending:
#  Sequence number/buffer (for IGT purposes): 0
#  ...
#  Transducer serial number: IS_PCD15287_01001
#  Transducer elements: 10
#  ...
#  Voltage [V]: [19.942205288284985]
#  Amplitude [%]: [85.01]
# 2026-08-25 11:57:13,576 - DEBUG - utils - onSequenceStart line 76 Listener: EXEC START
#   (buff: 0, count: 200, delay: 0)
# 2026-08-25 11:57:13,775 - DEBUG - utils - onPulseResult line 93     ch[0] V=21.8 V, I=0.385 A,
#   PhaseV/I=343.°, PhaseV/Vref=263.9°, Freq= 300000 Hz, Pow=8.01375 W
#
# Two channel-measurement formats exist, chosen by the driving system itself
# (onPulseResult()'s own channelMeasureCount() == 5 check) -- both are matched here, since which
# one a given setup reports isn't known ahead of time. The line number after "onPulseResult" is
# NOT matched on a fixed value (it shifts whenever utils.py itself is edited) -- only that it's
# present.

TIMESTAMP = r"(?P<timestamp>[\d\-]+ [\d:,]+)"

# No timestamp prefix on these four -- they're continuation lines of the multi-line "...with the
# following parameters is validated before sending:" debug message, so they don't carry their
# own timestamp (unlike EXEC_START_RE/PULSE_HEADER_RE/CHANNEL_RE_5/CHANNEL_RE_4 below).
SEQ_NUM_RE = re.compile(
    r"(?:Sequence number/buffer|Buffer number) \(for IGT purposes\):\s*(?P<seq_num>\d+)"
)
TRANSDUCER_SERIAL_RE = re.compile(r"Transducer serial number:\s*(?P<serial>\S+)")
TRANSDUCER_ELEMENTS_RE = re.compile(r"Transducer elements:\s*(?P<elements>\d+)")
VOLTAGE_RE = re.compile(r"Voltage \[V\]:\s*\[(?P<voltage>-?[\d.]+)\]")
AMPLITUDE_RE = re.compile(r"Amplitude \[%\]:\s*\[(?P<amplitude>-?[\d.]+)\]")

EXEC_START_RE = re.compile(
    TIMESTAMP + r".*Listener: EXEC START \(buff:\s*(?P<buff_label>\d+)"
)

PULSE_HEADER_RE = re.compile(
    TIMESTAMP + r".*onPulseResult line \d+.*"
    r"exec:\s*(?P<exec>\d+).*pulse:\s*(?P<pulse>\d+).*"
    r"duration:\s*(?P<duration>[\d.]+)\s*ms.*elapsed:\s*(?P<elapsed>[\d.]+)\s*ms"
)

# 5-measure format: V/I/PhaseV-I/PhaseV-Vref/Freq/Pow.
CHANNEL_RE_5 = re.compile(
    TIMESTAMP + r".*onPulseResult line \d+.*"
    r"ch\[(?P<channel>\d+)\]\s*"
    r"V=(?P<V>[\d.]+)\s*V,\s*"
    r"I=(?P<I>[\d.]+)\s*A,\s*"
    r"PhaseV/I=(?P<phase_vi>-?[\d.]+).*?,\s*"
    r"PhaseV/Vref=(?P<phase_vref>-?[\d.]+).*?,\s*"
    r"Freq=\s*(?P<freq>[\d.]+)\s*Hz,\s*"
    r"Pow=(?P<pow>-?[\d.]+)\s*W"
)

# 4-measure format: Vfwd/Vrev/PhaseV-Vref/Freq/Pow -- no per-channel current or PhaseV/I here.
CHANNEL_RE_4 = re.compile(
    TIMESTAMP + r".*onPulseResult line \d+.*"
    r"ch\[(?P<channel>\d+)\]\s*"
    r"Vfwd=(?P<Vfwd>[\d.]+)\s*V,\s*"
    r"Vrev=(?P<Vrev>[\d.]+)\s*V,\s*"
    r"PhaseV/Vref=(?P<phase_vref>-?[\d.]+).*?,\s*"
    r"Freq=\s*(?P<freq>[\d.]+)\s*Hz,\s*"
    r"Pow=(?P<pow>-?[\d.]+)\s*W"
)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="cp1252")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def _assign_channel_ranges(slots):
    """Give each slot (in the order it was configured) a consecutive channel range, sized by
    its own element count -- slot 1 gets [0, N1), slot 2 gets [N1, N1+N2), etc."""
    offset = 0
    ranged_slots = []
    for slot in slots:
        elements = slot["elements"] or 0
        ranged_slots.append({**slot, "channel_start": offset, "channel_end": offset + elements})
        offset += elements
    return ranged_slots


def parse_log(path: Path):
    """Returns (channel_df, exec_groups).

    exec_groups: [{'timestamp', 'buff_label', 'slots': [{'seq_num', 'serial', 'elements',
    'voltage', 'amplitude', 'channel_start', 'channel_end'}, ...]}, ...] -- one entry per
    "EXEC START" line, in order. 'slots' is a snapshot of whichever slot configurations had been
    seen so far (see this module's own docstring on why that isn't the same as the "Sequence
    number/buffer" label).
    """
    rows = []
    exec_groups = []

    pending_slots = []
    current_seq_num = None
    current_serial = None
    current_elements = None
    current_voltage = None
    current_group_index = None
    current_exec = None

    for line in read_text(path).splitlines():
        seq_num_match = SEQ_NUM_RE.search(line)
        if seq_num_match:
            current_seq_num = int(seq_num_match.group("seq_num"))
            current_serial = None
            current_elements = None
            current_voltage = None
            continue

        serial_match = TRANSDUCER_SERIAL_RE.search(line)
        if serial_match:
            current_serial = serial_match.group("serial")
            continue

        elements_match = TRANSDUCER_ELEMENTS_RE.search(line)
        if elements_match:
            current_elements = int(elements_match.group("elements"))
            continue

        voltage_match = VOLTAGE_RE.search(line)
        if voltage_match:
            current_voltage = float(voltage_match.group("voltage"))
            continue

        amplitude_match = AMPLITUDE_RE.search(line)
        if (amplitude_match and current_voltage is not None
                and current_elements is not None):
            pending_slots.append({
                "seq_num": current_seq_num,
                "serial": current_serial,
                "elements": current_elements,
                "voltage": current_voltage,
                "amplitude": float(amplitude_match.group("amplitude")),
            })
            continue

        exec_start_match = EXEC_START_RE.search(line)
        if exec_start_match:
            exec_groups.append({
                "timestamp": exec_start_match.group("timestamp"),
                "buff_label": int(exec_start_match.group("buff_label")),
                "slots": _assign_channel_ranges(pending_slots),
            })
            current_group_index = len(exec_groups) - 1
            continue

        header_match = PULSE_HEADER_RE.search(line)
        if header_match:
            current_exec = int(header_match.group("exec"))
            continue

        match_5 = CHANNEL_RE_5.search(line)
        if match_5:
            rows.append({
                "timestamp": match_5.group("timestamp"),
                "exec": current_exec,
                "exec_group": current_group_index,
                "channel": int(match_5.group("channel")),
                "format": "5-measure",
                "V": float(match_5.group("V")),
                "I": float(match_5.group("I")),
                "Vrev": None,
                "phase_vi_deg": float(match_5.group("phase_vi")),
                "phase_vref_deg": float(match_5.group("phase_vref")),
                "freq_hz": float(match_5.group("freq")),
                "pow_w": float(match_5.group("pow")),
            })
            continue

        match_4 = CHANNEL_RE_4.search(line)
        if match_4:
            rows.append({
                "timestamp": match_4.group("timestamp"),
                "exec": current_exec,
                "exec_group": current_group_index,
                "channel": int(match_4.group("channel")),
                "format": "4-measure",
                "V": float(match_4.group("Vfwd")),  # forward voltage stands in for "V" here
                "I": None,
                "Vrev": float(match_4.group("Vrev")),
                "phase_vi_deg": None,
                "phase_vref_deg": float(match_4.group("phase_vref")),
                "freq_hz": float(match_4.group("freq")),
                "pow_w": float(match_4.group("pow")),
            })

    if not rows:
        raise ValueError(
            "No ch[...] lines found. Does this log file's format still match the example at "
            "the top of this script? If not, share a snippet and the regex can be adjusted."
        )

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y-%m-%d %H:%M:%S,%f")
    return df, exec_groups


def print_exec_groups(exec_groups):
    if not exec_groups:
        print("No 'Listener: EXEC START' lines found -- no channel row can be associated with "
              "a specific execution/slot (expected values will be blank below).")
        return
    print("Executions found in log:")
    for i, group in enumerate(exec_groups):
        print(f"  execution {i} ({group['timestamp']}, buff label {group['buff_label']}):")
        if not group["slots"]:
            print("    no slot configuration found before this execution")
        for slot in group["slots"]:
            print(f"    ch[{slot['channel_start']}:{slot['channel_end']}) -> "
                  f"{slot['serial']} (sequence {slot['seq_num']}): "
                  f"voltage={slot['voltage']:.2f} V, amplitude={slot['amplitude']:.2f} %")


def _slot_for_channel(exec_groups, exec_group_index, channel):
    # exec_group_index arrives as a numpy/pandas scalar (float if the column has any NaN, e.g.
    # rows measured before the first EXEC START) rather than a plain int/None -- pd.isna() below
    # catches both "genuinely None" and "NaN from that float upcast" in one check.
    if pd.isna(exec_group_index):
        return None
    exec_group_index = int(exec_group_index)
    if exec_group_index >= len(exec_groups):
        return None
    for slot in exec_groups[exec_group_index]["slots"]:
        if slot["channel_start"] <= channel < slot["channel_end"]:
            return slot
    return None


def with_expected_values(channel_df: pd.DataFrame, exec_groups) -> pd.DataFrame:
    """Adds 'expected_voltage' and four deviation columns to a copy of channel_df, computed per
    row from whichever slot's channel range that row's channel falls into (_slot_for_channel()):
      - 'pct_deviation'/'abs_pct_deviation': percentage deviation, signed and unsigned.
      - 'deviation_v'/'abs_deviation_v': deviation in volts, signed and unsigned -- doesn't
        blow up for a channel with a small expected voltage the way the percentage versions do
        (e.g. a 0.02 V swing on a 0.43 V expected value is a ~5% swing in volts, but ~5x that in
        percentage terms purely because the denominator is small -- neither number is "wrong",
        they just answer different questions: percentage says how far off target relative to
        what was asked for, volts says the actual physical size of the swing).

    The signed/unsigned distinction matters for both units: a channel that swings evenly above
    and below its expected voltage can have a signed average close to 0 (looks fine) while every
    individual pulse is meaningfully off-target (the *_abs_* columns would show that). Rows with
    no known expected voltage, or an expected voltage of exactly 0 V (percentage deviation from
    a zero base is undefined), get NaN in the percentage columns -- the volt-based columns stay
    valid even then, since they don't divide by the expected voltage at all. Callers decide
    whether/how to filter."""
    with_expected = channel_df.copy()
    slots = with_expected.apply(
        lambda row: _slot_for_channel(exec_groups, row["exec_group"], row["channel"]), axis=1)
    with_expected["expected_voltage"] = slots.apply(lambda s: s["voltage"] if s else None)

    with_expected["deviation_v"] = with_expected["V"] - with_expected["expected_voltage"]
    with_expected["abs_deviation_v"] = with_expected["deviation_v"].abs()

    pct_base = with_expected["expected_voltage"].where(with_expected["expected_voltage"] != 0)
    with_expected["pct_deviation"] = (with_expected["deviation_v"] / pct_base) * 100
    with_expected["abs_pct_deviation"] = with_expected["pct_deviation"].abs()
    return with_expected


def summarize_channels(channel_df: pd.DataFrame, exec_groups) -> pd.DataFrame:
    # min/max are here specifically because mean/std alone can hide an occasional large
    # excursion (e.g. a channel that briefly drops to 15 V a handful of times out of 200 pulses
    # barely moves the mean, and only shows up as a somewhat elevated std) -- min/max show the
    # actual swing directly instead of having to infer it.
    summary = channel_df.groupby(["exec_group", "channel"])["V"].agg(
        n="count", mean_voltage="mean", std_voltage="std", min_voltage="min",
        max_voltage="max").reset_index()
    summary["cv_pct"] = (summary["std_voltage"] / summary["mean_voltage"]) * 100
    # Peak-to-peak swing (max - min) -- the single number for "how far did this channel actually
    # swing", instead of having to read both min/max columns and subtract them by eye. The
    # percentage version is relative to this channel's own mean (like cv_pct above), not to its
    # expected voltage -- a channel with a near-zero expected voltage would otherwise inflate a
    # tiny swing into a huge-looking percentage purely from a near-zero denominator (the same
    # problem pct_diff_from_expected/mean_abs_pct_deviation below don't have this issue with,
    # since they're never divided by a value close to zero for a channel actually driving
    # anything).
    summary["swing_voltage"] = summary["max_voltage"] - summary["min_voltage"]
    summary["swing_pct"] = (summary["swing_voltage"] / summary["mean_voltage"]) * 100

    slots = summary.apply(
        lambda row: _slot_for_channel(exec_groups, row["exec_group"], row["channel"]), axis=1)
    summary["serial"] = slots.apply(lambda s: s["serial"] if s else None)
    summary["expected_voltage"] = slots.apply(lambda s: s["voltage"] if s else None)
    summary["pct_diff_from_expected"] = (
        (summary["mean_voltage"] - summary["expected_voltage"])
        / summary["expected_voltage"]) * 100

    # Mean of the per-pulse *unsigned* deviation, in both percentage and volts -- deliberately
    # not derived from pct_diff_from_expected above (which is signed and computed from the mean
    # voltage, so opposite-direction swings within the same channel can cancel out and
    # understate how much it actually fluctuates pulse to pulse). The volt-based version doesn't
    # get inflated the way the percentage one does for a channel with a small expected voltage
    # (e.g. a 0.02 V swing looks huge in percent against a 0.43 V expected value, but is exactly
    # as small in volts as it is in absolute terms) -- see with_expected_values()'s own
    # docstring for why both are kept side by side rather than picking one.
    with_deviation = with_expected_values(channel_df, exec_groups)
    mean_abs_deviation = with_deviation.groupby(["exec_group", "channel"])[
        ["abs_pct_deviation", "abs_deviation_v"]].mean().reset_index()
    mean_abs_deviation = mean_abs_deviation.rename(columns={
        "abs_pct_deviation": "mean_abs_pct_deviation", "abs_deviation_v": "mean_abs_deviation_v"})
    summary = summary.merge(mean_abs_deviation, on=["exec_group", "channel"], how="left")

    return summary.sort_values(["exec_group", "channel"]).reset_index(drop=True)


def print_summary(summary: pd.DataFrame):
    print()
    print("Per-channel voltage summary:")
    print("(percentage difference is relative to that channel's own configured voltage, i.e. "
          "the slot whose channel range it falls into. pct_diff_from_expected is signed and "
          "based on the mean voltage -- opposite-direction swings can cancel out there; "
          "mean_abs_pct_deviation/mean_abs_deviation_v are the mean of each pulse's own "
          "unsigned deviation, so they don't cancel out -- the volt-based one doesn't inflate "
          "for a channel with a small expected voltage the way the percentage one does)")
    with pd.option_context("display.float_format", "{:.2f}".format):
        print(summary.to_string(index=False))


def find_extreme_pulses(channel_df: pd.DataFrame, n: int) -> pd.DataFrame:
    """The n lowest and n highest measured pulses for each channel, with when they happened
    (exec index/timestamp) and how far they sit from that channel's own mean -- so a "sometimes
    this channel spikes/dips" observation can be pinned down to specific pulses, rather than
    only knowing the overall min/max exists somewhere in 200+ measurements."""
    with_deviation = channel_df.copy()
    with_deviation["mean_v_for_channel"] = with_deviation.groupby("channel")["V"].transform(
        "mean")
    with_deviation["deviation_from_mean"] = (
        with_deviation["V"] - with_deviation["mean_v_for_channel"])

    per_channel = []
    for _, group in with_deviation.groupby("channel"):
        per_channel.append(group.nsmallest(n, "V"))
        per_channel.append(group.nlargest(n, "V"))
    extremes = pd.concat(per_channel)
    columns = ["channel", "exec", "timestamp", "V", "deviation_from_mean"]
    return extremes[columns].sort_values(["channel", "V"]).reset_index(drop=True)


def print_extreme_pulses(extremes: pd.DataFrame, n: int):
    print()
    print(f"Most extreme pulses per channel ({n} lowest / {n} highest measured voltage):")
    with pd.option_context("display.float_format", "{:.2f}".format):
        for channel, group in extremes.groupby("channel"):
            print(f"  channel {channel}:")
            for _, row in group.iterrows():
                print(f"    exec {int(row['exec'])} @ {row['timestamp']}: "
                      f"{row['V']:.2f} V ({row['deviation_from_mean']:+.2f} V from that "
                      "channel's own mean)")


def _channel_colors(channels):
    """Consistent tab20-based color per channel (20 clearly distinguishable colors, instead of
    matplotlib's default 10, which would otherwise repeat every 10 channels) -- also used to
    color the summary table's "Ch" column, so the table doubles as the legend."""
    import matplotlib.pyplot as plt
    cmap = plt.get_cmap("tab20")
    return {channel: cmap(i) for i, channel in enumerate(channels)}


def plot_voltage(channel_df: pd.DataFrame, exec_groups, summary: pd.DataFrame, logfile_name: str,
                 out_path: Path):
    """One self-contained image: the voltage-over-time plot, the SIGNED percentage-deviation-
    over-time plot right below it (sharing the same time axis), and a color-coded per-channel
    summary table (a trimmed subset of the same numbers printed to stdout by print_summary() --
    see the table-building code below for which columns and why), and a title naming which
    transducer(s)/configured voltage each execution used. Meant to be readable on its own,
    without needing the terminal output next to it."""
    # Imported here, not at module level, so a broken/missing matplotlib install only breaks
    # plotting -- the numeric summary above still runs regardless (see main()'s own try/except
    # around this call).
    import matplotlib.pyplot as plt

    # One voltage value per (exec, channel); each pulse round's own timestamp (shared by every
    # channel logged under that round's header, see _pivot_per_pulse()'s own comment) is used as
    # the time axis, in seconds since the start of the log. V is V (5-measure format) or Vfwd
    # (4-measure format) -- see parse_log()'s own comment.
    per_pulse = channel_df.groupby(["exec", "channel"], as_index=False).agg(
        timestamp=("timestamp", "first"), exec_group=("exec_group", "first"), V=("V", "first")
    )

    pivot, channels = _pivot_per_pulse(channel_df, "V")

    with_expected = with_expected_values(channel_df, exec_groups)
    with_expected = with_expected[with_expected["expected_voltage"].notna()]
    deviation_pivot, _ = _pivot_per_pulse(with_expected, "pct_deviation")

    # Also used to color-code the summary table's "Ch" column below, so the table doubles as the
    # legend for both plots instead of a separate one.
    color_by_channel = _channel_colors(channels)

    fig = plt.figure(figsize=(20, max(9, 0.35 * len(channels) + 5)))
    grid = fig.add_gridspec(2, 2, width_ratios=[1.6, 1], height_ratios=[1.3, 1], wspace=0.03,
                            hspace=0.12)
    ax_plot = fig.add_subplot(grid[0, 0])
    ax_deviation = fig.add_subplot(grid[1, 0], sharex=ax_plot)
    ax_table = fig.add_subplot(grid[:, 1])
    ax_table.axis("off")

    for channel in channels:
        ax_plot.plot(pivot.index, pivot[channel], marker="o", markersize=2, linewidth=1.5,
                     color=color_by_channel[channel])

    drawn_expected = set()
    group_indices = sorted(int(g) for g in per_pulse["exec_group"].unique() if pd.notna(g))
    for exec_group_index in group_indices:
        for slot in exec_groups[exec_group_index]["slots"]:
            key = (slot["serial"], slot["voltage"])
            if key in drawn_expected:
                continue
            drawn_expected.add(key)
            ax_plot.axhline(slot["voltage"], color="black", linestyle="--", linewidth=1,
                            label=f"{slot['serial']} expected ({slot['voltage']:.2f} V)")

    ax_plot.set_ylabel("Voltage (V)")
    ax_plot.legend(fontsize=8, loc="best")
    ax_plot.grid(True, alpha=0.3)
    ax_plot.tick_params(labelbottom=False)  # shares the x-axis with ax_deviation below it

    ax_deviation.axhspan(-5, 5, color="gray", alpha=0.15)
    ax_deviation.axhline(0, color="black", linewidth=1)
    for channel in channels:
        if channel in deviation_pivot.columns:
            ax_deviation.plot(deviation_pivot.index, deviation_pivot[channel], marker="o",
                              markersize=2, linewidth=1.5, color=color_by_channel[channel])
    ax_deviation.set_xlabel("Time (s)")
    ax_deviation.set_ylabel("Deviation (%)")
    ax_deviation.grid(True, alpha=0.3)

    # Summary table -- one row per (execution, channel), derived from the same summary DataFrame
    # print_summary() prints to stdout, but trimmed to a subset of its columns: the image has
    # limited width to stay legible, stdout doesn't. "n" is dropped since it's the same 200 for
    # every row here (see the exec-group description in the title instead); "Std (V)" is dropped
    # since cv_pct (std relative to this channel's own mean) already carries that information in
    # a directly comparable, normalized form. "Mean |% Dev|" is dropped too -- the table already
    # has three other percentage-based columns (cv_pct, swing_pct, % Diff), and unlike those,
    # this one is the same near-zero-expected-voltage-inflation-prone percentage
    # with_expected_values()'s own docstring warns about; "Mean |Dev| (V)" (kept) answers the
    # same "how far off target on average" question without that distortion, for every channel
    # regardless of its own expected voltage.
    column_labels = ["Ch", "Transducer", "Mean (V)", "CV %", "Min (V)", "Max (V)", "Swing (V)",
                     "Swing %", "Expected (V)", "% Diff", "Mean |Dev| (V)"]
    cell_text = []
    row_colors = []
    for _, row in summary.iterrows():
        cell_text.append([
            str(int(row["channel"])),
            str(row["serial"]) if pd.notna(row["serial"]) else "-",
            f"{row['mean_voltage']:.2f}",
            f"{row['cv_pct']:.1f}",
            f"{row['min_voltage']:.2f}",
            f"{row['max_voltage']:.2f}",
            f"{row['swing_voltage']:.2f}",
            f"{row['swing_pct']:.1f}",
            f"{row['expected_voltage']:.2f}" if pd.notna(row["expected_voltage"]) else "-",
            f"{row['pct_diff_from_expected']:+.1f}" if pd.notna(row["pct_diff_from_expected"])
            else "-",
            f"{row['mean_abs_deviation_v']:.3f}"
            if pd.notna(row["mean_abs_deviation_v"]) else "-",
        ])
        row_colors.append(color_by_channel.get(int(row["channel"]), "white"))

    table = ax_table.table(cellText=cell_text, colLabels=column_labels, loc="center",
                           cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.4)
    # Sizes each column to fit its actual rendered content (e.g. "Transducer" gets as much
    # width as the longest serial number needs, short numeric columns get correspondingly less)
    # instead of matplotlib's default equal-width columns, which either clips or overflows a
    # column like this one where content length varies a lot between columns.
    table.auto_set_column_width(col=list(range(len(column_labels))))
    for row_index, color in enumerate(row_colors):
        table[(row_index + 1, 0)].set_facecolor(color)  # +1 skips the header row

    title_lines = [f"Intensity log: {logfile_name}"]
    for i, group in enumerate(exec_groups):
        slots_descr = ", ".join(
            f"{s['serial']} ch[{s['channel_start']}:{s['channel_end']}) @ "
            f"{s['voltage']:.2f} V / {s['amplitude']:.1f} %" for s in group["slots"]
        ) or "no slot configuration found"
        title_lines.append(f"Execution {i} (buff label {group['buff_label']}): {slots_descr}")
    fig.suptitle("\n".join(title_lines), fontsize=10, ha="left", x=0.02)

    # fig.tight_layout() doesn't understand ax.table() (a Table isn't one of the artist types it
    # knows how to measure) and warns "results might be incorrect" -- subplots_adjust() sets the
    # same kind of margins directly instead, without needing to auto-measure every artist.
    fig.subplots_adjust(left=0.04, right=0.98, top=0.85, bottom=0.08, wspace=0.03)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def _pivot_per_pulse(df: pd.DataFrame, value_column: str):
    """Pivots df (already restricted to the rows/columns the caller wants) into one row per
    (exec, channel), time-indexed in seconds since the first pulse -- the shape plot_voltage()
    plots both its voltage and its signed-deviation panel against. Returns (pivot, channels).

    Pivots on "exec" (the pulse-round index shared by every channel logged under that round's
    single "onPulseResult" header), not on each row's own per-channel timestamp -- those
    timestamps differ by a few ms between channels within the same round (each channel's line is
    logged separately), so pivoting on them directly leaves ~5% of rows with a value for only
    one channel and NaN for every other -- matplotlib breaks the line at each such NaN, showing
    up as isolated, disconnected dots even though no data is actually missing. Pivoting on the
    round index instead guarantees every channel that fired in a given round shares the exact
    same row; the round's timestamp (for the x-axis) is taken as the mean across that round's own
    channels, since their few-ms spread doesn't matter once they're already grouped by round."""
    per_pulse = df.groupby(["exec", "channel"], as_index=False).agg(
        timestamp=("timestamp", "first"), value=(value_column, "first"))
    t_by_exec = per_pulse.groupby("exec")["timestamp"].mean()
    t0 = t_by_exec.min()
    t_s_by_exec = (t_by_exec - t0).dt.total_seconds()
    pivot = per_pulse.pivot_table(index="exec", columns="channel", values="value")
    pivot.index = pivot.index.map(t_s_by_exec)
    pivot.index.name = "t_s"
    return pivot, sorted(pivot.columns)


def process_logfile(logfile: Path, prefix: str = None):
    """Runs the full pipeline (parse -> stdout summary -> voltage.png) for one log file. Used
    both for the single-LOGFILE case and for each file found under LOG_DIR."""
    prefix = prefix or logfile.stem
    out_dir = logfile.parent

    try:
        channel_df, exec_groups = parse_log(logfile)
    except ValueError as e:
        # No onPulseResult lines in this particular file -- expected in LOG_DIR mode, where the
        # folder can contain a mix of native IGT logs, FDS info/debug logs, and other files that
        # never carry this data at all. Skip it rather than aborting the whole batch.
        print(f"Skipped {logfile.name} -- {e}")
        return

    print(f"Read {len(channel_df)} row(s), {channel_df['channel'].nunique()} channel(s), "
          f"{channel_df['exec'].nunique()} pulse(s), format(s): "
          f"{sorted(channel_df['format'].unique())}")
    print()
    print_exec_groups(exec_groups)

    summary = summarize_channels(channel_df, exec_groups)
    print_summary(summary)

    if N_EXTREMES > 0:
        extremes = find_extreme_pulses(channel_df, N_EXTREMES)
        print_extreme_pulses(extremes, N_EXTREMES)

    try:
        voltage_png_path = out_dir / f"{prefix}_voltage.png"
        plot_voltage(channel_df, exec_groups, summary, logfile.name, voltage_png_path)
        print(f"Plot written: {voltage_png_path}")
    except ImportError as e:
        print(f"\nSkipped plotting -- matplotlib isn't usable in this environment ({e}). "
              "The numbers above are unaffected; fix the matplotlib/numpy install to also get "
              "the plots.")


def main():
    if LOG_DIR:
        logfiles = sorted(
            p for p in Path(LOG_DIR).iterdir()
            if p.is_file() and p.suffix.lower() in (".txt", ".log"))
        if not logfiles:
            print(f"No .txt/.log files found in {LOG_DIR}")
            return
        for logfile in logfiles:
            print(f"\n{'=' * 80}\n{logfile.name}\n{'=' * 80}")
            process_logfile(logfile)
    else:
        process_logfile(Path(LOGFILE), OUTPUT_PREFIX)


if __name__ == "__main__":
    main()
