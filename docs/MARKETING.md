# Phone Farm Marketing Strategy

## One-Liner

> Drop an APK. AI finds the bugs. Free, local, open source.

## The Hook

Every Android developer has the same workflow: build APK, install on phone, tap around manually, hope nothing breaks. Phone Farm replaces the "tap around and hope" step with an AI that systematically explores every screen.

**Not a test framework.** Not "write YAML scripts." Not "set up a device lab." Just: give it an APK, get a bug report.

---

## Target Audience (in priority order)

### 1. Solo Android developers (Largest group, easiest to reach)
- Pain: No QA team, no budget for BrowserStack, testing is manual
- Message: "Free QA engineer that runs on your laptop"
- Where: r/androiddev, Twitter #AndroidDev, Dev.to

### 2. Indie studios / small teams (2-10 devs)
- Pain: Can't afford $129/mo BrowserStack, Firebase free tier is limited
- Message: "BrowserStack alternative that costs $0"
- Where: r/gamedev, Indie Hackers, Discord communities

### 3. AI/MCP enthusiasts (Growing fast, high engagement)
- Pain: Looking for useful MCP servers, tired of toy demos
- Message: "First MCP server that controls a real Android phone"
- Where: r/ClaudeAI, r/LocalLLaMA, MCP Discord, Twitter #MCP

### 4. QA professionals (Smaller but high-value for Pro)
- Pain: Scripted tests break on every UI change
- Message: "Tests that don't break when the UI changes"
- Where: r/QualityAssurance, Ministry of Testing, LinkedIn

---

## Launch Sequence

### Pre-heat (Day -2 to -1)

**Day -2: Dev.to article**
- [ ] Publish: "I replaced my QA team with an AI agent (and it's free)"
- [ ] Tags: `#android`, `#testing`, `#opensource`, `#ai`
- [ ] Cross-post to Hashnode (custom domain blog for SEO)
- [ ] This gets picked up by [daily.dev](https://daily.dev) passively — millions of devs see curated posts

**Day -1: Reddit soft launch**
- [ ] r/selfhosted (~400K subs) — "I built X to solve Y" framing. This community drove 1,200 GitHub stars for Usertour in early 2025
- [ ] r/opensource (~100K subs) — welcomes project announcements with technical story
- [ ] r/SideProject (~150K subs) — explicitly allows project sharing

### Launch Day (Day 0 — Tuesday or Wednesday)

**Morning: Hacker News (8-9 AM PT)**
- [ ] Submit: "Show HN: Phone Farm — Free, local-first AI-powered Android QA testing"
- [ ] Link directly to GitHub repo (NOT a marketing page — repos get more stars)
- [ ] First comment: 60-word TL;DR + seed question: "What does your mobile QA workflow look like?"
- [ ] Reply to every comment within 10 minutes for first 2 hours
- [ ] Have 5-10 people ready for genuine comments in first 30 minutes
- [ ] Avoid: superlatives ("revolutionary"), clickbait, linking to landing page

**Same day: Twitter/X thread**
```
I built a free, open-source alternative to BrowserStack for Android testing.

Drop an APK. An AI agent explores your app, finds bugs, writes a report.

No scripts. No cloud. No monthly bill.

Here's how it works: [thread with demo GIF]
```
- Hashtags: only 1-2 per post (more gets penalized 40%). Use `#opensource` + `#AndroidDev`
- Tag: @AndroidDev (official Google account), @JakeWharton
- Also post on [Bluesky](https://bsky.app) — 30M+ users, strong developer/OSS community migrated from Twitter

**Same day: Product Hunt**
- [ ] Category: Developer Tools > Engineering & Development
- [ ] First comment: founder story + specific problem + "I'd love your feedback" (NOT "please upvote")
- [ ] Comment quality now outweighs votes in 2026 algorithm — 50 upvotes + 30 genuine comments > 200 upvotes + 5 comments
- [ ] Have 50+ supporters ready at launch for genuine feedback

### Day +1: Amplify

- [ ] LinkedIn personal narrative: "Why I built Phone Farm" — tag [top software dev creators](https://linkhub.gg/en/top-creators-2025/category/software-development)
- [ ] r/androiddev — post in "Show us what you've built" weekly thread (NOT standalone — mods are strict)
- [ ] r/QualityAssurance (~30K subs) — niche but exact audience
- [ ] Post on [Peerlist](https://peerlist.io) Projects section

### Day +3: YouTube

- [ ] **Primary video: 2-3 minutes** — install → boot → QA test → results. No fluff
- [ ] **YouTube Short: under 60 seconds** — "Watch this AI find a bug in 30 seconds" (high shareability)
- [ ] Embed demo GIF in GitHub README (single highest-impact thing for repo conversion)
- [ ] Algorithm rewards watch-time relative to length — 2min video watched to completion > 15min with 30% retention

### Week 2: Expand

- [ ] Submit PR to [awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) GitHub repo
- [ ] r/ClaudeAI: "I built an MCP server that lets AI agents test Android apps"
- [ ] Reply to existing "Android testing tools" threads on Reddit/Stack Overflow
- [ ] Email Android dev newsletters
- [ ] Post in Discord communities:

| Discord | Why |
|---------|-----|
| [Android Dev](https://discord.gg/android) | Direct audience |
| [Test Automation University](https://discord.gg/testautomationu) | QA professionals |
| [Reactiflux](https://discord.gg/reactiflux) (~200K) | Cross-pollination, many mobile devs |
| [The Coding Den](https://discord.gg/code) (~100K+) | Has showcase channel |

### Week 3+: Sustain

- [ ] Weekly "What I shipped" updates on Twitter + Bluesky
- [ ] Answer Stack Overflow questions about Android testing, mention Phone Farm where relevant
- [ ] Write comparison post: "Phone Farm vs BrowserStack vs Firebase Test Lab"
- [ ] Contribute to discussions in r/androiddev about testing
- [ ] Track trending position on [Trendshift.io](https://trendshift.io)

---

## Content Pieces

### 1. Demo GIF (Do this FIRST — nothing else matters without it)
Record a 30-second GIF showing:
1. `phone-farm demo` command
2. Emulator booting
3. AI exploring the Wikipedia app
4. Bug report appearing

Tools: `adb screenrecord` for emulator, `asciinema` for terminal, combine with ffmpeg.

### 2. Dev.to Article (Day -2)
Title: "I replaced my QA team with an AI agent (and it's free)"
- Show the problem (manual testing sucks)
- Show the solution (one command)
- Show results (real bug report with screenshots)
- Link to GitHub
- Publish 2 days before HN — builds initial stars for social proof

### 3. Twitter/Bluesky Thread (Day 0)
Build-in-public narrative with demo GIF. Threads outperform single tweets for dev content.

### 4. Comparison Table Post (Week 3)
"I tested my app with BrowserStack ($129/mo), Firebase Test Lab, and Phone Farm (free). Here's what each found."
Real results, real comparison, real screenshots.

---

## Reddit Etiquette (Critical)

- **80/20 rule**: 80% genuine participation, 20% your own stuff. Reddit shadowbans self-promo accounts
- Read each sub's sidebar rules. Many have specific self-promo threads
- Frame as problem-solving: "I was frustrated with manual Android QA so I built..." NOT "Announcing Phone Farm"
- Reply to every comment on your post
- Never coordinate upvotes — Reddit detects and penalizes this

---

## GitHub Optimization

### Topics (already added)
android, android-testing, qa-automation, mcp, ai-testing, appium, emulator, mobile-testing, bug-detection, test-automation

### README badges (already added)
PyPI version, downloads, stars, tests passing, license

### Issue templates (already added)
Bug report, Feature request, App showcase

### Additional
- [ ] Enable GitHub Discussions for community engagement
- [ ] Pin a "Getting Started" discussion
- [ ] Use GitHub Releases with proper changelogs for each update
- [ ] Stars velocity matters more than total: 100 stars in 24 hours > 1,000 over 6 months for trending

---

## Metrics to Track

| Metric | Target (30 days) | Target (90 days) |
|--------|-------------------|-------------------|
| GitHub stars | 100 | 500+ |
| PyPI installs | 200 | 1,000 |
| Dev.to views | 5,000 | - |
| HN points | 50+ | - |
| Discord/community members | 20 | 100 |
| Contributors | 3 | 10 |

Key insight: Getting to 1,000 stars in the first week signals momentum. The pre-heat + stagger strategy is designed for this.

---

## What NOT to Do

- Don't compare to Maestro on scripting — you'll lose. Compare on **exploration**
- Don't say "AI-powered" without showing results. Always lead with the demo GIF
- Don't launch on multiple platforms the same day. Stagger for sustained visibility
- Don't ask for stars. Ship useful updates and stars follow
- Don't build Pro features until Community has 200+ stars. Validate demand first
- Don't coordinate upvote drives — Reddit and Product Hunt detect and penalize this in 2026

---

## Pro Conversion Strategy (After 200+ Stars)

1. Free users discover Phone Farm, use deterministic explorer
2. They see ROADMAP.md — "AI vision testing finds 10x more bugs"
3. They try `phone-farm qa-test` with their own API key (BYOK)
4. Power users want multi-device, CI/CD, regression detection
5. Offer Pro at $29/mo or Team at $99/mo/seat

**The free version is the funnel. The AI is the upgrade.**
