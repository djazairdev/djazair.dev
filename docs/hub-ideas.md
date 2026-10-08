# Hub ideas

Anyone can propose an open-source project that would help people in Algeria, and anyone with a GitHub account can vote for it. Every quarter, djazair.dev adopts the idea with the most votes and builds it in the open, in the djazairdev organisation on GitHub (PRD HUB-07, ticket [#39](https://github.com/djazairdev/djazair.dev/issues/39)).

Ideas and votes live in GitHub Discussions, in an **Ideas** category, so there is no database and no djazair.dev account. Every 6 hours the Hub sync reads the votes, and the Hub shows the round and the five ideas with the most votes.

Discussions and its Ideas category are enabled. The Home participation cards link to the proposal form and the ideas sorted by votes; the Hub explains how proposals, voting and quarterly adoption work. Set `config.HUB_IDEAS` to `False` if Discussions is disabled later: Home shows the idea and voting paths as coming soon, and the Hub hides its Ideas section.

## How the vote works

- **Proposing.** The [form](../.github/DISCUSSION_TEMPLATE/ideas.yml) asks for the problem, who benefits, a champion who will lead the project, and the skills it needs. Anyone with a GitHub account can post one.
- **Voting.** A vote is the discussion's upvote: one per GitHub account, and it can be taken back. GitHub does the counting, so nobody can vote twice.
- **Rounds.** Each calendar quarter, in UTC, is a round. Votes carry over from one round to the next until an idea is adopted or closed.
- **The count.** The first Hub sync after a round closes saves its count: the ten open ideas with the most votes, as GitHub counted them then. The sync runs every 6 hours, so votes cast in the first hours of the new quarter still count. The count is saved once and never changed, on the `hub-data` branch ([`ideas.json`](https://github.com/djazairdev/djazair.dev/blob/hub-data/ideas.json)), and the Hub links to it.
- **Ties.** Between ideas with the same number of votes, the earlier one ranks first.

## Adoption

Once a round's count is saved, the maintainers go down it, top first. The first idea that meets all three of these is adopted:

1. **At least 10 votes.** The number is `IDEAS_MIN_VOTES` in [`site/djsite/config.py`](../site/djsite/config.py); the Hub and the form say the same, and a test keeps them in step.
2. **A champion** ready to lead it. The form's *Champion* field names them; a maintainer checks with them in the discussion.
3. **The maintainers' review.** The project is open source, legal and useful to people in Algeria, doesn't duplicate an active project, and the organisation can look after it. The review also looks for unusual voting, such as many new accounts voting for one idea at once.

When an idea is passed over, say why in its discussion. If no idea meets all three, nothing is adopted that quarter, and the votes carry over.

Then:

1. **Create the repository** in the djazairdev organisation, with an open licence, a README, a CONTRIBUTING file and the `djazairdev` topic, and give the champion the *Maintain* role.
2. **Label the idea** `adopted` and post the repository link in the discussion. At the next sync the idea leaves the vote and shows under *Adopted so far* on the Hub.
3. **List it in the Hub** once it meets the [seven checks](../CONTRIBUTING.md#list-a-project-in-the-hub), like any other project.
4. **Announce it** in the next quarterly report, in its *What djazair.dev did* section ([reports.md](reports.md)).

## What is saved

`python -m hub ideas` ([`hub/ideas.py`](../hub/ideas.py)) writes `data/derived/hub/ideas.json`, and the Hub sync saves it on the `hub-data` branch with the rest of the snapshot:

```json
{
 "about": "Project ideas from the Ideas category of GitHub Discussions, ranked by votes (…)",
 "generated_at": "2027-01-01T00:41:00Z",
 "category": "https://github.com/djazairdev/djazair.dev/discussions/categories/ideas",
 "ideas": [
  {"number": 12, "url": "https://github.com/djazairdev/djazair.dev/discussions/12",
   "title": "Open bus timetables for Algiers", "created_at": "2026-10-20T09:14:00Z",
   "votes": 34, "comments": 6, "champion": true, "skills": ["data", "web"], "status": "open"}
 ],
 "rounds": [
  {"quarter": "2026-Q4", "counted_at": "2027-01-01T00:41:00Z",
   "ranking": [{"number": 12, "url": "https://github.com/djazairdev/djazair.dev/discussions/12",
                "title": "Open bus timetables for Algiers", "votes": 34, "champion": true}]}
 ]
}
```

- `ideas` lists the open ideas by votes, then the adopted ones. A closed idea that wasn't adopted is left out.
- `rounds` holds each round's count, the ten open ideas with the most votes.
- **No personal data.** Nothing says who proposed, voted or commented. For the champion it keeps only whether there is one, and the only text kept is the title, with "Idea:" and @mentions taken out. The idea's text is read in memory, for the champion and the skills, and never written.
- While Discussions is off, `category` is `null` and both lists are empty.

GitHub's GraphQL API needs a token, so run it locally with one. `--repo owner/name` reads another repository's *ideas* category instead, to try it before Discussions is on here:

```sh
GITHUB_TOKEN=… python3 -m hub ideas    # writes data/derived/hub/ideas.json
```

## Turn it on

Repository settings need an admin; each step takes a minute.

1. **Turn on Discussions:** Settings → General → Features → Discussions.
2. **Check the category:** GitHub usually creates an *Ideas* category with Discussions. Open it and check that its address ends in `/discussions/categories/ideas`: the slug must be `ideas`, because GitHub picks the form by file name ([`.github/DISCUSSION_TEMPLATE/ideas.yml`](../.github/DISCUSSION_TEMPLATE/ideas.yml)) and the Hub sync reads that category. If there is no such category, create it (Discussions → Categories → New category, name `Ideas`, format *Open-ended discussion*). Set its description to *Ideas for open-source projects that would help people in Algeria. Upvote the ones you want built.*
3. **Create the label:** Issues → Labels → New label: `adopted`, with the description *Adopted by the djazairdev organisation.* Discussions use the repository's labels.
4. **Optional:** remove the other default categories you don't want (General, Q&A, Show and tell, Polls). Keep *Announcements* if you plan to post release notes there.
5. **Show it on the Hub:** in [`site/djsite/config.py`](../site/djsite/config.py), set `HUB_IDEAS = True`, run the tests and open a pull request. After the deploy, the Hub shows the vote between the projects and "Get listed": the round, the five ideas with the most votes, the rules, *Propose an idea* and *See all ideas*. The About page's privacy section then says the Hub shows ideas and their votes, never who proposed or voted for them.
6. **Fill the list:** run the Hub sync by hand (Actions → *Hub sync* → *Run workflow*). It needs nothing more: the workflow already has `discussions: read`.
7. Open a new idea to check the form, then delete it.

The first round is what is left of that quarter. If little is left, the maintainers can skip adopting from its count: the votes carry over.

## Looking after ideas

- **Duplicates:** close the newer one with a link to the older, so its voters can vote there. Closed ideas leave the vote.
- **Not an idea:** move support questions to an issue, and lock or delete spam.
- **Titles:** the Hub shows each idea's title. Edit one that doesn't say what the project is.
- **No champion:** an idea whose champion says "wanted" gathers votes like any other, but can't be adopted until someone offers to lead it in the discussion and the *Champion* field is edited. Hackathon organisers looking for projects can start there.
- **Before a meetup or hackathon:** *See all ideas* sorts the category by votes. Share the first few with the organisers.
