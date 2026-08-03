# -*- coding: utf-8 -*-
"""
Tests for fus_driving_systems.igt.transducerXYZ.Transducer.

computePhases is pure trig/geometry -- it only calls pulse.frequencyCount()
and pulse.frequency(i), so a small duck-typed fake pulse is used instead of
a real unifus.Pulse, keeping these tests independent of the native
extension entirely.

loadFromString/_loadConfig parse an in-memory .ini-style string -- no disk
I/O needed. load() itself does real file I/O via open() and is covered by
one light test using tmp_path.
"""
import pytest

from fus_driving_systems.igt import transducerXYZ


class _FakePulse:
    """Duck-typed stand-in for unifus.Pulse: computePhases only reads
    frequencyCount()/frequency(i), never touches phases/amplitudes."""

    def __init__(self, frequencies):
        self._frequencies = frequencies

    def frequencyCount(self):
        return len(self._frequencies)

    def frequency(self, i):
        return self._frequencies[i]


def _transducer_with_elements(elements_m):
    """Builds a Transducer with elements set directly (bypassing
    load/loadFromString), which is all computePhases needs."""
    trans = transducerXYZ.Transducer()
    trans.elements = elements_m
    return trans


class TestComputePhases:

    def test_computes_phase_as_fractional_wavelength_times_360(self):
        # SOUND_SPEED_WATER is 1500 m/s (real config default). With a
        # single 1.5 MHz frequency, wavelength = 1500 / 1_500_000 = 1 mm.
        # Elements placed at 0, 0.25, 0.5, 0.75 mm depth (in meters) along
        # Z therefore sit at 0, 1/4, 1/2, 3/4 of a wavelength from the
        # aim point at the origin.
        trans = _transducer_with_elements([
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.00025),
            (0.0, 0.0, 0.0005),
            (0.0, 0.0, 0.00075),
        ])
        pulse = _FakePulse([1_500_000])

        phases = trans.computePhases(pulse, (0, 0, 0), set_focus_mm=50,
                                     dephasing_degree=None)

        assert phases == pytest.approx([0.0, 90.0, 180.0, 270.0])

    def test_computes_phase_per_element_frequency_when_multiple_frequencies(self):
        # freqCount > 1 requires freqCount == channelCount(); each element
        # then uses its own frequency (and therefore its own wavelength).
        trans = _transducer_with_elements([
            (0.0, 0.0, 0.00025),
            (0.0, 0.0, 0.0005),
        ])
        # element 0: 1.5 MHz -> wavelen 1mm -> 0.25mm = quarter wave -> 90 deg
        # element 1: 750 kHz -> wavelen 2mm -> 0.5mm = quarter wave -> 90 deg
        pulse = _FakePulse([1_500_000, 750_000])

        phases = trans.computePhases(pulse, (0, 0, 0), set_focus_mm=50,
                                     dephasing_degree=None)

        assert phases == pytest.approx([90.0, 90.0])

    def test_applies_dephasing_offset_cyclically_across_elements(self):
        trans = _transducer_with_elements([
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.00025),
            (0.0, 0.0, 0.0005),
            (0.0, 0.0, 0.00075),
        ])
        pulse = _FakePulse([1_500_000])

        # base phases (no dephasing) would be [0, 90, 180, 270]; with a
        # dephasing step of 90 degrees, nth_elem = round(360/90) = 4, so
        # element i gets + (90 * i), then the cycle resets (it never does,
        # since there are exactly 4 elements here).
        phases = trans.computePhases(pulse, (0, 0, 0), set_focus_mm=50,
                                     dephasing_degree=[90.0])

        assert phases == pytest.approx([0.0, 180.0, 360.0, 540.0])

    def test_exits_when_no_frequencies_defined(self):
        trans = _transducer_with_elements([(0.0, 0.0, 0.0)])
        pulse = _FakePulse([])  # frequencyCount() == 0

        with pytest.raises(SystemExit):
            trans.computePhases(pulse, (0, 0, 0), set_focus_mm=50, dephasing_degree=None)

    def test_exits_when_first_frequency_is_zero(self):
        trans = _transducer_with_elements([(0.0, 0.0, 0.0)])
        pulse = _FakePulse([0])

        with pytest.raises(SystemExit):
            trans.computePhases(pulse, (0, 0, 0), set_focus_mm=50, dephasing_degree=None)

    def test_exits_when_frequency_count_mismatches_element_count(self):
        trans = _transducer_with_elements([(0.0, 0.0, 0.0), (0.0, 0.0, 0.00025)])
        pulse = _FakePulse([1_500_000, 750_000, 500_000])  # 3 freqs, 2 elements

        with pytest.raises(SystemExit):
            trans.computePhases(pulse, (0, 0, 0), set_focus_mm=50, dephasing_degree=None)

    def test_exits_when_dephasing_degree_has_more_than_one_entry_that_does_not_match(self):
        trans = _transducer_with_elements([(0.0, 0.0, 0.0), (0.0, 0.0, 0.00025)])
        pulse = _FakePulse([1_500_000])

        with pytest.raises(SystemExit):
            trans.computePhases(pulse, (0, 0, 0), set_focus_mm=50,
                               dephasing_degree=[10.0, 20.0])


class TestLoadFromString:

    def test_parses_elements_section_into_meter_coordinates(self):
        trans = transducerXYZ.Transducer()
        definition = (
            "[elements]\n"
            "size = 2\n"
            "1 = 0|0|10\n"
            "2 = 5|5|20\n"
        )

        result = trans.loadFromString(definition)

        assert result is True
        assert trans.channelCount() == 2
        assert trans.elements == pytest.approx([
            (0.0, 0.0, 0.01),
            (0.005, 0.005, 0.02),
        ])

    def test_exits_when_size_key_is_missing(self):
        trans = transducerXYZ.Transducer()
        definition = "[elements]\nnotsize = 2\n"

        with pytest.raises(SystemExit):
            trans.loadFromString(definition)

    def test_exits_when_size_is_zero(self):
        trans = transducerXYZ.Transducer()
        definition = "[elements]\nsize = 0\n"

        with pytest.raises(SystemExit):
            trans.loadFromString(definition)

    def test_exits_when_an_element_entry_is_malformed(self):
        trans = transducerXYZ.Transducer()
        definition = (
            "[elements]\n"
            "size = 1\n"
            "1 = not|enough\n"
        )

        with pytest.raises(SystemExit):
            trans.loadFromString(definition)

    def test_exits_on_empty_string_via_missing_section_not_empty_content_check(self):
        """
        FINDING: loadFromString's own 'empty content' guard
        (`if config.readfp(stringio) == []:`) can never fire --
        ConfigParser.readfp()/read_file() always returns None, never a
        list, so that comparison is always False regardless of input.
        An empty string therefore does NOT hit the 'Error: empty content'
        message; it falls through to _loadConfig(), where
        config.getint('elements', 'size') raises NoSectionError (no
        [elements] section at all), caught by _loadConfig's bare `except:`
        and reported as "Error: missing 'elements.size' parameter" instead
        -- the same path as test_exits_when_size_key_is_missing above.
        Still a SystemExit either way, just via a different, slightly
        misleading message than the one the code appears to intend for
        this case.
        """
        trans = transducerXYZ.Transducer()

        with pytest.raises(SystemExit):
            trans.loadFromString("")


class TestLoad:

    def test_load_reads_file_and_parses_elements(self, tmp_path):
        """Light test for the real-file-I/O path of load() -- the parsing
        itself is already covered in depth by TestLoadFromString."""
        trans = transducerXYZ.Transducer()
        def_file = tmp_path / "transducer.ini"
        def_file.write_text(
            "checksum=DEADBEEF\n"
            "\n"
            "[elements]\n"
            "size = 1\n"
            "1 = 1|2|3\n"
        )

        result = trans.load(str(def_file))

        assert result is True
        assert trans.elements == pytest.approx([(0.001, 0.002, 0.003)])

    def test_load_exits_when_file_does_not_exist(self, tmp_path):
        trans = transducerXYZ.Transducer()
        missing = tmp_path / "does_not_exist.ini"

        with pytest.raises(SystemExit):
            trans.load(str(missing))
