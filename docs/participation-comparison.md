# Participation-first comparison

The `participation-first` branch starts from `hero-replay` at
`b65b0954719e3dbaaa8b40476ae2cdde7d776122`. The original page remains available on
that branch. This variant changes Home and the Hub's matching controls, while
retaining the bilingual Index, data downloads, map replay, chart effects and footer.

## Seven proposals

1. **Lead with a developer benefit.** Home explains finding a project and building
   together. Contribution and local teammate actions precede the account statistics.
2. **Show an immediate next step.** Up to three varied actual open issues from the Hub
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
   points to GitHub Discussions. Votes guide priority. During the pilot there is no minimum vote count;
   adoption requires a champion and maintainer review.
6. **Give visitors a reason to return.** A saved filter URL stays in localStorage
   on their device. A returning Home visit restores those filters; a dedicated
   link opens the saved Hub view. GitHub Watch instructions explain optional
   issue, pull request and discussion notifications.
7. **Show public participation evidence.** Listed projects link to their merged
   pull requests and show their last recorded commit. Snapshot contributor metrics
   appear when available, including zero. No testimonials or activity are invented.

A saved search is a filter, not a frozen issue list. It is device- and origin-specific;
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

## Review refinements (9 October 2026)

Home now uses a small varied issue preview and links to two additional public
Algerian projects: dzcode.io and Laravel Algerian Cities. Licences, repository
status, contribution instructions and default-branch commit dates were verified
against GitHub on 9 October. They are editorial discovery links in
`content/community-projects.json`, separate from the opted-in Hub registry; they
have no reply pledge and do not claim a particular task is available or unassigned.
The weekly link check covers their repository and contribution URLs. Review
activity, licences and contribution instructions again before updating the
checked date, and remove a project if its contribution path stops being usable.

The repeated contribution card is removed from Ideas. The empty board has a
direct proposal button and explains discussion and champion matching. The pilot
removes the ten-vote adoption gate while retaining review in vote order, champion
and feasibility requirements; the proposal template and governance docs match.
GitHub reads that template from its default branch, so its public form changes
when these branch changes merge, not when a preview is deployed.

Public progress and saved-search options now share one section. Project language
and saved-search labels state what the controls actually do. The full scorecard
and trend chart are replaced by a compact Index gateway. Existing Home chart
downloads and embeds remain published with a source anchor on that gateway.
The original `hero-replay` branch remains unchanged.
