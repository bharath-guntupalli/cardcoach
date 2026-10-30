# CardCoach

CardCoach checks what a credit card actually earned and cost. Open this public repository, install the skill on your own Gemini or Claude account, then chat about your own unlocked statement.

This is not regulated financial advice. It does not guarantee savings, and it does not suggest spending more to earn rewards. Bank rules change. The skill looks the current rule up and records the page and the date.

Repository: <https://github.com/bharath-guntupalli/cardcoach>

Do not commit statements, passwords, or full card numbers. Upload a statement only inside your own chat.

## For friends

1. Open this repository.
2. Download one zip:
   - Gemini: [dist/cardcoach-gemini.zip](dist/cardcoach-gemini.zip)
   - Claude: [dist/cardcoach-claude.zip](dist/cardcoach-claude.zip)
3. Upload that zip as a skill on your own account. Steps are below. These products do not offer a share button on a personal account, so each person installs the zip once.
4. Unlock the statement on your own computer, then add that unlocked file to a new chat and ask for an audit.

Gemini zip upload works on [gemini.google.com](https://gemini.google.com) and the Gemini app on a Mac. Claude zip upload works on [claude.ai](https://claude.ai). Checked 30 Oct 2026: [Gemini skills](https://support.google.com/gemini/answer/17094296), [Claude skills](https://support.claude.com/en/articles/12512180-use-skills-in-claude).

### Gemini

1. Sign in at [gemini.google.com](https://gemini.google.com). You need to be 18 or over, with Keep Activity on.
2. Open Customize, then Skills.
3. Choose Create, then Upload.
4. Select `cardcoach-gemini.zip`. The zip already contains the `cardcoach` folder Gemini expects.
5. Start a new chat. Type `/cardcoach`, or just ask for a statement audit.

### Claude

1. Sign in at [claude.ai](https://claude.ai).
2. Open Customize, then Skills.
3. Choose Create skill, then Upload a skill.
4. Select `cardcoach-claude.zip`.
5. Turn the skill on.
6. Start a new chat and ask for a statement audit.

### Unlock the statement, then chat

Bank PDFs are often password-protected. Remove the password on your own computer. Do not paste the password or a one-time code into the chat.

```bash
qpdf --password=YOUR_PASSWORD --decrypt statement.pdf statement-unlocked.pdf
```

Add `statement-unlocked.pdf` to the chat. If you already have a spreadsheet of the rows, you can add that instead. Then say:

> Here is my unlocked card statement. The bank is ____ and the card is ____. Audit the rewards and fees.

The example rates in [examples/](examples/) are fictional. A real audit uses your statement and a current page from the bank.

ChatGPT is a separate paste-in project, not a zip. See [SHARE.md](SHARE.md). Do not join one shared ChatGPT project. Members of a shared project can see its chats and files.

## Run the auditor

Python 3.9 or newer. From a clone, this fictional example should print `"ok": true`. The February statement's 50 points are January's reward, so February's extra spend is not treated as a mistake.

```bash
PYTHONPATH=src python3 -m cardcoach audit \
  --transactions examples/transactions.csv \
  --rules examples/rules.json \
  --summary examples/summary.json
```

The program prints JSON and exits with status 1 when the rows do not match the statement summary. Rewards are not audited for a statement that fails that check. `python3 -m pip install -e ".[dev]"` also installs a `cardcoach` command and pytest.

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

## Layout

```text
canon/CARDCOACH.md          source prompt
src/cardcoach/              tested maths
packs/build_packs.py        writes the packs and dist/ from the canon
packs/claude/cardcoach/     SKILL.md, references/, scripts/
packs/gemini/cardcoach/     same shape, Gemini tool notes
packs/chatgpt/              project instructions and knowledge files
dist/                       zips and ChatGPT files to hand to someone
examples/                   fictional rows, not a real statement
```

`packs/build_packs.py` also copies the Claude skill to `.cursor/skills/cardcoach/` for this workspace. Rebuild after any edit to the canon or the engine:

```bash
python3 packs/build_packs.py
```

## Contributing

Fork the repository, change [canon/CARDCOACH.md](canon/CARDCOACH.md) or [src/cardcoach/](src/cardcoach/), then rebuild the packs so the generated files stay in sync. Run `python3 -m pytest`. Open a pull request.

Do not commit statements, PDFs, passwords, or full card numbers.

## Privacy

Mask card numbers to the last four digits. The chat packs say the same. A shared ChatGPT project shows every member the project's chats and files, so this repository does not use one as the way to share CardCoach.
