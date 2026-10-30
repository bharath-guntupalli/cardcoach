# Share CardCoach

Send people this repository. They download a zip from `dist` and install it on their own account. `dist` is short for distribution. It is the download folder. `canon` is the master copy of the instructions. Friends do not need to open it.

Their statements stay in their own chat. The zip has instructions and the maths only. Do not put a statement, a password, or a full card number into a Gem, a skill, or a project you then share.

Product help below was fetched on 30 Oct 2026.

## What a friend does

### Gemini

You need to be 18 or over, with Keep Activity on, signed in at [gemini.google.com](https://gemini.google.com) or in the Gemini app on a Mac.

1. Download [dist/cardcoach-gemini.zip](dist/cardcoach-gemini.zip).
2. Open Customize, then Skills.
3. Choose Create, then Upload.
4. Select the zip. It must contain `cardcoach/SKILL.md`.
5. Start a chat and ask for a statement audit, or type `/cardcoach`.

Source: [Create and manage skills](https://support.google.com/gemini/answer/17094296). A personal Gemini account cannot share a skill yet. [Gems to skills](https://support.google.com/gemini/answer/18560919) says sharing is coming in the next few weeks.

### ChatGPT

1. Download the three files in [dist/chatgpt/](dist/chatgpt/): `PROJECT_INSTRUCTIONS.md`, `CARDCOACH.md`, and `cardcoach_audit.py`.
2. On [chatgpt.com](https://chatgpt.com), create a project named CardCoach.
3. Open project settings and paste `PROJECT_INSTRUCTIONS.md` into the instructions. The file is under 6,000 characters.
4. Add `CARDCOACH.md` and `cardcoach_audit.py` as project files. Leave room for a statement. A free project allows 5 files.
5. In a chat inside that project, upload only your own unlocked statement.

Source: [Projects in ChatGPT](https://help.openai.com/en/articles/10169521-projects-in-chatgpt). Project instructions replace the account-wide custom instructions. Those account-wide boxes hold 1,500 characters on Free and Go, and 5,000 on paid plans. This pack uses the project box.

Do not accept an invite to someone else's CardCoach project. Members can see that project's chats and files. A free account can also hold only 5 people in one project.

### Claude

1. Download [dist/cardcoach-claude.zip](dist/cardcoach-claude.zip).
2. Open Customize, then Skills.
3. Choose Create skill, then Upload a skill.
4. Upload the zip and turn the skill on.
5. Start a new chat and add your own unlocked statement.

Source: [Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude). On Free, Pro, and Max, each person uploads the skill. Sharing exists on Team and Enterprise and stays inside that organisation. Anthropic's [distribution guide](https://claude.com/resources/guides/the-complete-guide-to-building-skills-for-claude/distribution-and-sharing) describes the same download-and-upload path.

## Unlock the statement

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
qpdf --password=YOUR_PASSWORD --decrypt statement.pdf statement-decrypted.pdf
```

## If you are publishing a link yourself

Do this once, from the account that owns the pack. If a product gives you a URL, paste it into [README.md](README.md).

### ChatGPT

Create the project as above, with the two knowledge files and no statement. Keep that project as your own.

A new custom GPT link is not available on a personal account. OpenAI's help, fetched 30 Oct 2026, says Free, Go, Plus, and Pro accounts cannot create a new GPT: [Sharing and publishing GPTs](https://help.openai.com/en/articles/8798878-sharing-and-publishing-gpts).

Do not set a project to "Anyone with the link." [Projects help](https://help.openai.com/en/articles/10169521-projects-in-chatgpt) allows that link, and anyone who joins can see the project's chats and files. The owner can include 5 people on Free, 10 on Plus and Go, and 100 on Pro.

### Claude

Upload `dist/cardcoach-claude.zip` once to confirm it loads. Friends use the same zip from this repository. A personal account has no share URL.

### Gemini

Upload `dist/cardcoach-gemini.zip` the same way a friend does.

Until 17 Nov 2026 you can also make a Gem. Paste [packs/gemini/GEM_INSTRUCTIONS.txt](packs/gemini/GEM_INSTRUCTIONS.txt), upload `CARDCOACH.md` as knowledge, and share it as Viewer with specific people or "Anyone with the link." Do not choose Public, and do not make anyone an Editor. [Share a Gem](https://support.google.com/gemini/answer/16504957) shows the instructions and knowledge files to anyone with access. Chats stay separate unless you share a chat.

[Gems help](https://support.google.com/gemini/answer/15146780) says personal-account Gems become read-only on 17 Nov 2026 and are removed on 17 Dec 2026. Keep the zip. When Gemini lets a personal account share a skill, put that URL in the README and drop the Gem.

## Try this

> Here is my unlocked card statement. The bank is ____ and the card is ____. Audit the rewards and fees.
