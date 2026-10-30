# Share CardCoach

Send people this repository, or the files in `dist/`. Each person installs a copy on their own account. Their statements stay in their own chat.

The packs contain instructions and the auditor only. Do not put a statement, a password, or a full card number into a Gem, a skill, or a project you then share.

Product help below was fetched on 30 Oct 2026.

## What a friend does

### Gemini

Friend requirements: 18 or over, Keep Activity on, signed in at [gemini.google.com](https://gemini.google.com) or the Gemini app on a Mac.

1. Download [dist/cardcoach-gemini.zip](dist/cardcoach-gemini.zip).
2. Open Customize, then Skills.
3. Choose Create, then Upload.
4. Select the zip. It must contain `cardcoach/SKILL.md`.
5. Start a chat and ask for a statement audit, or type `/cardcoach`.

Source: [Create and manage skills](https://support.google.com/gemini/answer/17094296). Personal Gemini Apps cannot share a skill yet. [Gems-to-skills](https://support.google.com/gemini/answer/18560919) says sharing arrives in the coming weeks.

### ChatGPT

1. Download the three files in [dist/chatgpt/](dist/chatgpt/): `PROJECT_INSTRUCTIONS.md`, `CARDCOACH.md`, and `cardcoach_audit.py`.
2. On [chatgpt.com](https://chatgpt.com), create a project named CardCoach.
3. Open project settings and paste `PROJECT_INSTRUCTIONS.md` into the instructions. The file is under 6,000 characters.
4. Add `CARDCOACH.md` and `cardcoach_audit.py` as project files. Leave room for a statement. A free project allows 5 files.
5. In a chat inside that project, upload only your own statement.

Source: [Projects in ChatGPT](https://help.openai.com/en/articles/10169521-projects-in-chatgpt). Project instructions replace global custom instructions. Global custom instructions are 1,500 characters on Free and Go, and 5,000 on paid plans. This pack uses the project box, not the global box.

Do not accept an invite to someone else's CardCoach project. Members can see that project's chats and files. A free account can also hold only 5 collaborators.

### Claude

1. Download [dist/cardcoach-claude.zip](dist/cardcoach-claude.zip).
2. Open Customize, then Skills.
3. Choose Create skill, then Upload a skill.
4. Upload the zip and turn the skill on.
5. Start a new chat and upload your own statement.

Source: [Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude). On Free, Pro, and Max, each person uploads the skill. Sharing exists on Team and Enterprise and stays inside that organization. Anthropic's [distribution guide](https://claude.com/resources/guides/the-complete-guide-to-building-skills-for-claude/distribution-and-sharing) describes the same download-and-upload path.

## What you publish

Do this once, from the account that owns the pack. Then paste any URL you get into the table in [README.md](README.md).

### ChatGPT

Create the project as above, with the two knowledge files and no statement. That project is for you.

Optional easy link: build a Custom GPT, paste the same project instructions (they are under the 8,000-character box people report for GPTs), upload the same two knowledge files, and set sharing to "Anyone with a link." Each person who opens the link gets their own chat. That is different from a shared project.

Do not set a project to "Anyone with the link." [Projects help](https://help.openai.com/en/articles/10169521-projects-in-chatgpt) allows that link, and anyone who joins can see the project's chats and files. Collaborator caps are 5 on Free, 10 on Plus and Go, and 100 on Pro.

### Claude

Upload `dist/cardcoach-claude.zip` once to confirm it loads. Friends use the same zip from this repository. There is no personal-account URL to paste.

### Gemini

Upload `dist/cardcoach-gemini.zip` the same way a friend does.

Optional bridge until 17 Nov 2026: create a Gem, paste [packs/gemini/GEM_INSTRUCTIONS.txt](packs/gemini/GEM_INSTRUCTIONS.txt), upload `CARDCOACH.md` as knowledge, and share it as Viewer with specific people or "Anyone with the link." Do not choose Public, and do not make anyone an Editor. [Share a Gem](https://support.google.com/gemini/answer/16504957) shows the instructions and knowledge files to anyone with access. Chats stay separate unless you share a chat.

[Gems help](https://support.google.com/gemini/answer/15146780) says personal-account Gems become read-only on 17 Nov 2026 and are removed on 17 Dec 2026. The zip is the copy to keep. When Gemini lets personal accounts share a skill, put that URL in the README and retire the Gem.

## Try this

> Here is my card statement. The bank is ____ and the card is ____. Audit the rewards and fees.

Decrypt PDFs locally. Do not paste a password or a one-time code.

```bash
qpdf --password=YOUR_PASSWORD --decrypt statement.pdf statement-decrypted.pdf
```
