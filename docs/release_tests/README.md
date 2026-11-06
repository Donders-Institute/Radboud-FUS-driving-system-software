# Release tests

Before a release, the software is tested by three people, each from their own side. The test plans
and the filled-in reports of a release are kept here, one folder per release, so that it stays on
record what was tested, by whom and on which version.

| Role | Plan | What it covers | Hardware needed |
|---|---|---|---|
| User | `FDS_user_testplan.md` | Is the README clear, can you install it, can you run the GUI and the example scripts with protocol files | Yes, an IGT on a dummy load (section E of the plan) |
| Programmer | `FDS_programmer_testplan.md` | Automated tests, safety-critical limits, packaging, code review of the critical paths | No |
| Maintainer | `FDS_maintainer_testreport.md` | The hardware tests on every Python version, on a system with an active calibration, oscilloscope checks, and the example scripts on a dummy load | Yes |

## How to use a plan

1. Copy the plan for your role and name the copy `FDS_<role>_testreport.md` (for example
   `FDS_user_testreport.md`).
2. Fill in the header: the exact version (tag or commit) you test, the date, your name, your
   environment. The maintainer tells you which Python version to use.
3. Work through the items. Mark an item `- [x]` when it passes. If it fails, or you could not do it,
   leave it unmarked and write why on the `Result:` line. Anything unclear in the instructions
   counts as a finding too.
4. Sign at the bottom for what you did, and send the report back to the maintainer, who adds it to
   the folder of the release.

Test the version you were given. If the code changes after you tested, the maintainer tells you
which items to redo.
