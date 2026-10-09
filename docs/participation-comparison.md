# Participation-first comparison

The `participation-first` branch starts from `hero-replay` at
`b65b0954719e3dbaaa8b40476ae2cdde7d776122`. The original page remains available on
that branch. This variant changes Home and the Hub's matching controls, while
retaining the bilingual Index, data downloads, map replay, chart effects and footer.

## Seven proposals

1. **Lead with a developer benefit.** Home explains finding a project and building
   together. Contribution and local teammate actions precede the account statistics.
2. **Show an immediate next step.** Up to six actual open issues from the Hub
   snapshot follow the hero, with requirements, maintainer labels and direct links.
   A short expandable guide explains a first contribution.
3. **Match contributions.** Home filters by suggested task type, repository
   language and keywords. Matching searches open the full Hub, which keeps its
   existing beginner-label, project and age filters and adds the same task types.
   Issue dates and snapshot freshness are visible. A reply pledge is explicitly
   distinguished from measured response time.
4. **Make local collaboration concrete.** founders.coffee remains the source for
   cities, sessions and RSVP. Visitors can bring an issue or host a session; the
   site does not invent local events or promise availability.
5. **Make ideas actionable.** Home displays the current ideas round when the Hub
   snapshot provides it, with votes and status. Before that snapshot exists it
   points to GitHub Discussions. Adoption still requires votes, a champion and
   maintainer review.
6. **Give visitors a reason to return.** A saved filter URL stays in localStorage
   on their device. A returning Home visit restores those filters; a dedicated
   link opens the saved Hub view. GitHub Watch instructions explain optional
   issue, pull request and discussion notifications.
7. **Show public participation evidence.** Listed projects link to their merged
   pull requests and show their last recorded commit. Snapshot contributor metrics
   appear when available, including zero. No testimonials or activity are invented.

A saved view is a filter, not a frozen issue list. It is device- and origin-specific;
preview and production do not share it. There is no new account system, email list,
job board or background subscription. Core content and links remain usable without
JavaScript. Matching and saved views need JavaScript; the Home GET form passes
the chosen filters to the Hub.

## Compare outcomes

Use the same Hub snapshot for both variants when judging the content. Show each
variant to developers with different experience levels, alternate which they see
first, and ask them to find a task they could attempt, find a local teammate, and
explain how they would propose an idea. Record task completion, confusion, time to
find a useful action and whether they return to their saved view. Ask about their
recent contribution attempts rather than whether they "like" the features.

Do not treat more clicks as proof of more contributions. Follow through to a real
issue comment, draft pull request, session RSVP or proposed idea where participants
choose to share the result. Use those findings to decide which parts to merge.
