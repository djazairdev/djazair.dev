# Hub ideas

Project ideas for the Hub live in GitHub Discussions, in an **Ideas** category (PRD HUB-07, ticket [#39](https://github.com/djazairdev/djazair.dev/issues/39)). Anyone can post an idea with a form that asks for the problem, who benefits, a champion and the skills needed. An idea is marked **adopted** once its champion links a repository, and the best go to hackathons and djazair.dev meetups.

Everything is ready in the repository, but Discussions is off until a maintainer turns it on. Until then the Hub doesn't show its Ideas section, so no link leads nowhere.

## Turn it on

Repository settings need an admin; each step takes a minute.

1. **Turn on Discussions:** Settings → General → Features → Discussions.
2. **Check the category:** GitHub usually creates an *Ideas* category with Discussions. Open it and check that its address ends in `/discussions/categories/ideas`: the slug must be `ideas`, because GitHub picks the form by file name ([`.github/DISCUSSION_TEMPLATE/ideas.yml`](../.github/DISCUSSION_TEMPLATE/ideas.yml)). If there is no such category, create it (Discussions → Categories → New category, name `Ideas`, format *Open-ended discussion*). Set its description to *Ideas for open-source projects that would help people in Algeria.*
3. **Create the label:** Issues → Labels → New label: `adopted`, with the description *The champion linked a repository.* Discussions use the repository's labels.
4. **Optional:** remove the other default categories you don't want (General, Q&A, Show and tell, Polls). Keep *Announcements* if you plan to post release notes there.
5. **Show it on the Hub:** in [`site/djsite/config.py`](../site/djsite/config.py), set `HUB_IDEAS = True`, run the tests and open a pull request. After the deploy, the Hub shows the Ideas section between the projects and "Get listed", with *Propose an idea* and *Browse ideas*.
6. Open a new idea to check the form, then delete it.

## Looking after ideas

- **Adopted:** when a champion posts a repository link, check it is a real start (a README is enough) and add the `adopted` label. Once the project meets the [seven checks](../CONTRIBUTING.md#list-a-project-in-the-hub), suggest listing it.
- **No champion:** an idea whose champion says "wanted" stays open; organisers looking for hackathon projects start there.
- **Not an idea:** move support questions to an issue, and lock or delete spam.
- **Before a meetup or hackathon:** sort the category by top votes and share the first few with the organisers.
