# FDS 3.0 test plan: user

You test the software as a user would, with only the README and the documentation as your
guide. You do not need to know how it works inside. Where you get stuck, or something is unclear,
write it down: that is exactly what this test is for.

Most of this plan runs without hardware: section D uses built-in Mock driving systems. Section E
needs a real IGT driving system on a dummy load.

| | |
|---|---|
| Version tested (tag or commit) | |
| GUI version and FDS version shown in the window title | |
| Date | |
| Name | |
| Windows version | |
| Python version used (route B) | 3.11 (please use this one) |
| Time spent | |

Mark an item `- [x]` when it passes. If it fails, or you could not do it, leave it unmarked and
write why on the `Result:` line.

## A. The README

- [ ] **U1** Before you start, read "Getting Started" in the README. Without asking anyone you can say what the
  software controls, that it needs Windows, and which of the two ways (the GUI, or your own Python scripts)
  fits you.
  Result:

## B. Install and start the GUI

Do this **twice**, once for each route, on a computer where you have not installed the software
before (or in a fresh folder).

The README sends you to the release page and the release source. Until the release exists, the maintainer
gives you the program (a zip file) and the exact version of the source (a branch or commit) instead, and
you follow the README from there. Write down where you got them.

**Route 1: the ready-made program**

- [ ] **U2** Get `FDS_GUI-*-windows.zip` where the maintainer tells you (after the release it is on the
  release page, as the README describes). The README makes clear which file to take.
  Result:
- [ ] **U3** Extract it and double-click `FDS_GUI.exe`. The window opens.
  Result:
- [ ] **U4** Windows or your antivirus shows a warning when you start it. Write down what it says
  and what you did. The README says what to expect and what to choose: was that what you saw, and did it
  work? (A warning is a finding, not a failure.)
  Result:
- [ ] **U5** The window title shows the GUI version and the FDS version, and they match what the maintainer
  told you to expect.
  Result:
- [ ] **U6** You can find `ds_config.ini` where the README says it is
  (`_internal/fus_driving_systems/config/ds_config.ini` next to `FDS_GUI.exe`).
  Result:

**Route 2: Python**

- [ ] **U7** Install Python 3.11 from python.org (the maintainer asks you to use this version).
  Write down the exact version.
  Result:
- [ ] **U8** Get the source of the version the maintainer tells you (Step 1 of `docs/python-usage.md` describes the
  options, for example cloning and checking out a branch or tag).
  Result:
- [ ] **U9** Run `create_venv.bat` as described. Answer `y` when it asks about the GUI. It ends with
  "Setup complete", without errors. If you passed no Python path and it complained, note what the
  message said and whether you understood what to do.
  Result:
- [ ] **U10** Check the setup as "Step 3: Verify the Successful Setup" describes.
  Result:
- [ ] **U11** Start the GUI from the activated environment with `python -m fus_ds_gui.app`. The
  window opens.
  Result:

## C. Using the package from a script (no hardware needed)

- [ ] **U12** Follow "Usage" in `docs/python-usage.md` up to opening an example script in an editor
  (Steps 1 to 4).
  Result:
- [ ] **U13** Open `example_protocols/single_transducer/igt/standalone_plain.py` and read the comments.
  You understand what each part does, and which values you would change for your own experiment.
  Result:
- [ ] **U14** Load a protocol file without hardware. From the repository folder, with the
  environment activated:

  ```
  python -c "from fus_driving_systems.protocol_loader import load_protocol; print(load_protocol('example_protocols/single_transducer/igt/direct_execute.yaml')[0][0])"
  ```

  It prints a summary of the protocol (power, focus, frequency and the timing), without an
  error.
  Result:
- [ ] **U15** Run the example script without a driving system connected. It stops with a message you can
  understand, and not with a crash. Write down what the message says. (Connecting an IGT can take
  half a minute before it gives up; that is expected.)
  Result:

- [ ] **U16** Write a small protocol file of your own, following `docs/building-protocols.md` (copy an
  example and change a value, or start from the format described there), and load it with the command
  from U14. It loads, or the error tells you what to fix. Write down every place where
  the documentation did not tell you enough.
  Result:

## D. The GUI with the Mock driving systems (no hardware)

Open the **Planning** tab and choose **Mock IGT (no real hardware)**. Repeat this section with
the Sonic Concepts Mock if you have time.

- [ ] **U17** Build a protocol in Demo mode: choose a transducer, a focus, a power and a duration, then
  press Apply. The validation line under the form says "No problems found".
  Result:
- [ ] **U18** Enter a power above the limit. The message tells you what went wrong and what the allowed
  value is, in words you understand.
  Result:
- [ ] **U19** Enter a total duration that does not fit the pulse repetition interval (for example 2.5 s at 5 Hz).
  A red message explains the problem.
  Result:
- [ ] **U20** Switch to Advanced mode and back. The values you had are still there and nothing changes
  that you did not do yourself.
  Result:
- [ ] **U21** Save the protocol, load it again, and approve it (Approve protocol). Then change the saved file in an
  editor and load it again: the program notices that it is no longer approved.
  Result:
- [ ] **U22** Load an example into the GUI: **Load protocol...**, then
  `example_protocols/single_transducer/igt/direct_execute.yaml`. The form shows what the file says (compare the
  focus, power, frequency, pulse duration and interval, the pulse train and the total duration with the
  file), and Advanced mode is switched on because the file has a pulse train.
  Result:
- [ ] **U23** Make a typing mistake on purpose: copy that example, remove the last digit of the
  `transducer_serial`, and load it. The slot shows an error that names the problem, says that focus and
  power are reset when you choose a transducer, and shows the values from the file. Choose the right
  transducer and fill the values in again: the slot works.
  Result:
- [ ] **U24** Open the **Executing** tab: Connect, then Send (it shows "Sending protocol..." and then a
  confirmation), then Execute. A countdown runs and it ends with a confirmation.
  Result:
- [ ] **U25** Execute again and press Abort during the countdown. It stops cleanly and you can Execute
  again.
  Result:
- [ ] **U26** Tick "Use external trigger" and arm the protocol. The message says it is waiting, and the Mock
  fires after a few seconds.
  Result:
- [ ] **U27** The console panel shows the steps that were taken. You can find the log files and you know
  which folder they are in.
  Result:
- [ ] **U28** Add a second transducer slot in Advanced mode. When the form gets taller than the window, a
  scrollbar appears, and scrolling over a number field does not change its value.
  Result:
- [ ] **U29** Disconnect. The status says "Not connected" and Connect works again.
  Result:

## E. A real IGT driving system

Only the IGT is tested. This section is required, except U34, which needs a trigger source: it covers the
GUI and the script route with a protocol file, the two ways users run their own protocols. If there is no
hardware or no time for it, do not skip it silently: do the rest of the plan, leave these items unmarked with
"no hardware" on the Result line, and tell the maintainer. The maintainer then covers the same steps, and the
release notes say that this part was not done by a user. The maintainer tells you which driving system and
transducer to use. The pressure is 0.5 MPa. Follow your local
safety rules, use a dummy load (the resistors) or the setup that is meant for testing, and never run it on
a person or an animal.

- [ ] **U30** With the ready-made program (route 1), connect to the IGT from the GUI. It says "Connected".
  Result:
- [ ] **U31** Send and execute a short protocol at 0.5 MPa (the limit of Demo mode is 0.6 MPa). It completes and
  the console shows no errors.
  Result:
- [ ] **U32** Abort a running protocol. The output stops and the program stays usable.
  Result:
- [ ] **U33** Run a protocol file through a script from start to end:
  `example_protocols/single_transducer/igt/standalone_direct_execute.py`, which reads `direct_execute.yaml`.
  Change the driving system in the file to the one the maintainer told you to use, and the pressure to 0.5 MPa.
  The script connects, sends, executes and disconnects, and the log says the protocol executed successfully.
  Write down every step where you had to guess, and any message you did not understand.
  Result:
- [ ] **U34** (only with a trigger source) The same with `standalone_wait_for_trigger.py`, which reads
  `wait_for_trigger.yaml`. After you send the trigger, the protocol runs and the script ends.
  Result:

## F. Your judgement

- What was the most confusing step or sentence?
- What did you expect to find in the README or the documentation and did not?
- How long did the installation take you from start to a working GUI?
- Would you trust it for your own experiments? What would make you trust it more?
- Anything else?

## Sign-off

I did the items marked above, on the version and environment in the header.

Name:  Date:
