# CardCoach

CardCoach checks what a credit card actually earned and what it cost. This repository is public. Download a zip, install it on your own Gemini or Claude account, then chat about your own statement.

This is not financial advice. Savings are not guaranteed, and spending more just to earn rewards is a bad idea. Bank rules change, so the skill looks up the current page and writes down the date it was fetched.

https://github.com/bharath-guntupalli/cardcoach

Keep statements, passwords, and full card numbers out of this repository. Put a statement only in your own chat.

## For friends

1. Open this repository.
2. Download one zip from the `dist` folder. The name is short for distribution. That folder is the one with the files you install. You can ignore the rest.
   - Gemini: [dist/cardcoach-gemini.zip](dist/cardcoach-gemini.zip)
   - Claude: [dist/cardcoach-claude.zip](dist/cardcoach-claude.zip)
3. Upload the zip as a skill on your own account. The steps are below. Personal accounts have no share button, so each person does this once.
4. Unlock the statement, add the unlocked file to a new chat, and ask for an audit.

`canon` is the master copy of the instructions the skill follows. The zips are built from [canon/CARDCOACH.md](canon/CARDCOACH.md). You do not need to open that file to use CardCoach.

Gemini accepts the zip on [gemini.google.com](https://gemini.google.com) and in the Gemini app on a Mac. Claude accepts it on [claude.ai](https://claude.ai). Product help, fetched 30 Oct 2026: [Gemini skills](https://support.google.com/gemini/answer/17094296), [Claude skills](https://support.claude.com/en/articles/12512180-use-skills-in-claude).

### Gemini

1. Sign in at [gemini.google.com](https://gemini.google.com). You need to be 18 or over, with Keep Activity on.
2. Open Customize, then Skills.
3. Choose Create, then Upload.
4. Select `cardcoach-gemini.zip`. The zip already contains the `cardcoach` folder Gemini expects.
5. Start a new chat. Type `/cardcoach`, or ask for a statement audit.

### Claude

1. Sign in at [claude.ai](https://claude.ai).
2. Open Customize, then Skills.
3. Choose Create skill, then Upload a skill.
4. Select `cardcoach-claude.zip`.
5. Turn the skill on.
6. Start a new chat and ask for a statement audit.

### Unlock the statement

Do this on your own phone or computer. Do not type the password, or a one-time code, into the chat.

On a phone:

1. Open the statement PDF.
2. Enter the password when the phone asks for it.
3. Open the print option.
4. Save the file as a PDF on the phone.
5. Upload that saved PDF in the chat.

The saved file is no longer password protected, so the agent can read it.

On a computer, if you have `qpdf`:

```bash
qpdf --password=YOUR_PASSWORD --decrypt statement.pdf statement-unlocked.pdf
```

Add `statement-unlocked.pdf` to the chat. A spreadsheet of the rows works too. Then say:

> Here is my unlocked card statement. The bank is ____ and the card is ____. Audit the rewards and fees.

The rates in [examples/](examples/) are made up. A real audit uses your statement and a current page from the bank.

ChatGPT has no zip. The steps are in [SHARE.md](SHARE.md). Do not join someone else's CardCoach project. People in a shared project can see its chats and files.

## Run the maths on your computer

Python 3.9 or newer. From a clone, this made-up example should print `"ok": true`. The February statement's 50 points are January's reward, so the extra February spend is not a mistake.

```bash
PYTHONPATH=src python3 -m cardcoach audit \
  --transactions examples/transactions.csv \
  --rules examples/rules.json \
  --summary examples/summary.json
```

The program prints JSON and exits with status 1 when the rows do not match the statement summary. It skips the reward check for a statement that fails that test. `python3 -m pip install -e ".[dev]"` also installs a `cardcoach` command and pytest.

The formulas in [src/cardcoach/engine.py](src/cardcoach/engine.py) are:

```text
rounded = (amount // rounding_unit) * rounding_unit
points = rounded * rate
net = rewards - annual_fee * (1 + tax_rate) - opportunity_cost + benefit_value
```

Tests:

```bash
python3 -m pytest
```

## Folders

```text
canon/CARDCOACH.md          master instructions the skill follows
src/cardcoach/              the maths, with tests
packs/build_packs.py        builds the zips from canon/CARDCOACH.md
packs/claude/cardcoach/     Claude skill
packs/gemini/cardcoach/     Gemini skill
packs/chatgpt/              ChatGPT project text and files
dist/                       zips and ChatGPT files to download
examples/                   made-up rows, not a real statement
```

`packs/build_packs.py` also copies the Claude skill to `.cursor/skills/cardcoach/` for this workspace. After you edit the master instructions or the maths, rebuild:

```bash
python3 packs/build_packs.py
```

## Contributing

Fork the repository. Change [canon/CARDCOACH.md](canon/CARDCOACH.md) or [src/cardcoach/](src/cardcoach/), then rebuild so the zips match. Run `python3 -m pytest` and open a pull request.

Do not commit statements, PDFs, passwords, or full card numbers.

## Privacy

The skill masks card numbers down to the last four digits. A shared ChatGPT project shows every member the project's chats and files, so this repository does not use one shared project as the way to hand CardCoach around.
