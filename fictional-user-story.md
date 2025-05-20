Bonnie's Engineering Journal Journey

The Developer

Bonnie is a senior software engineer at a fintech startup. She's been coding for 10 years, but recently noticed she's losing track of her work's narrative. "Why did I make that architecture decision three months ago?" became a frustrating refrain during code reviews.

One Minute In

Bonnie runs mcp-commit-story init after reading about the tool on Hacker News. She installs the git hook and makes a small commit.

### 3:15 PM — Commit e4b7c9a

## Summary
Fixed validation bug where empty email addresses were being accepted in the user registration flow.

## Accomplishments
- Updated validateUserInput function in auth.js
- Added proper email validation regex
- Updated tests to cover edge case

## Terminal Commands (AI Session)  
- `npm test` - Ran test suite
- `git diff auth.js` - Reviewed changes
- `git commit -m "fix: validate email addresses properly"`

## Behind the Commit
- Commit: e4b7c9a
- Message: "fix: validate email addresses properly"
- Files: src/auth.js, tests/auth.test.js
Bonnie reads it and smiles. "Huh, this actually captures what I did perfectly. I can already see the terminal commands the AI ran for me."

One Day Later

Bonnie's made 6 commits today, working on a complex feature for merchant onboarding. She opens today's journal file:

# Daily Journal - 2025-05-16

### 9:30 AM — Commit d2f4a1b
[merchant schema design entry]

### 11:15 AM — Commit 7f3b9e2  
[API endpoint implementation]

### 2:45 PM — Commit 3a8c5d1
[database migration]

### 4:20 PM — Commit 9b6e4f8
[validation rules update]

### 5:30 PM — Commit 1c9f2a3
[frontend integration]

### 6:45 PM — Commit 5d8b7c2
[bug fix for edge case]
Bonnie scrolls through, remembering her day. "Oh right, that's when Cursor and I went back and forth about the schema design in the chat. And here's when I got stuck on that validation bug - I can see I ran npm test five times in a row!"

She adds a reflection: mcp-commit-story add-reflection "The merchant schema needs to handle international addresses better. This will be tricky but important for our Q3 global expansion."

One Week Later

Bonnie uses the summarization feature: mcp-commit-story summarize --week

# Week Summary - May 12-18, 2025

## Overview
Major progress on the merchant onboarding system, completing the core workflow and beginning international address support. Significant debugging session around email validation edge cases led to more robust user registration.

## Key Accomplishments
- Implemented merchant registration API (15 commits across 3 days)
- Resolved email validation bug affecting 0.1% of registrations
- Started international address support (schema design phase)
- Improved test coverage in auth module from 78% to 94%

## Major Decisions
- Chose PostgreSQL's JSONB for flexible international address storage over creating separate country-specific tables
- Decided to validate emails on both frontend and backend rather than client-only
- Moved from REST to GraphQL for merchant endpoints to reduce over-fetching

## Challenges & Frustrations
- Spent 4 hours debugging timezone issues in merchant dashboard
- International phone number validation more complex than expected
- AI assistant struggled with understanding legacy merchant table relationships

## Related Entries
- Daily entries: 2025-05-12 through 2025-05-18
- Key commits: d2f4a1b, 7f3b9e2, 3a8c5d1, 9b6e4f8
Bonnie feels energized reading this. "I haven't felt this clear about my work in years. Look at everything I accomplished! And I love how it captured that decision about JSONB - future me will thank me for documenting that reasoning."

One Month Later

Bonnie's manager asks her to write a post for the engineering blog about the merchant onboarding project. She runs: mcp-commit-story blogify journal/daily/2025-05-*.md

# Building Global Merchant Onboarding: A Month-Long Journey

## The Challenge
In early May 2025, our team embarked on building a merchant onboarding system that needed to handle businesses from around the world. What seemed like a straightforward CRUD operation quickly revealed the complexity of international business validation.

## Architecture Decisions
One of our first major decisions was choosing how to store international addresses. After exploring several options, including separate tables for each country's address format, we opted for PostgreSQL's JSONB columns. This gave us the flexibility to handle everything from Japanese addresses (which read from largest to smallest administrative divisions) to Brazilian addresses (which include specific neighborhood designators).

## The Email Validation Saga
Sometimes the smallest features lead to the biggest insights. A seemingly simple email validation bug taught us about the edge cases in international email formats and the importance of server-side validation. After debugging several failed registrations, we discovered that our regex was too restrictive for international domain names.

## Lessons Learned
Building for a global audience requires constant questioning of assumptions. Every field we thought was "standard" - phone numbers, postal codes, business names - had international variations we hadn't considered...
Bonnie reads through the generated blog post. "This is amazing! It turned my daily grind into a coherent narrative. I just need to polish a few sentences and add some code examples."

Her manager reads the draft: "Bonnie, this is exactly the kind of technical storytelling we want more of. How did you remember all these details so clearly?"

One Year Later

Bonnie is now using the journal for performance reviews, job interviews, and conference talk proposals. She runs mcp-commit-story summarize --range "2024-05-01:2025-05-01" to see her full year.

What Bonnie Does With the Output:

1. Performance Reviews

She uses monthly summaries to remember all her contributions. "I had 47 major accomplishments, solved 12 critical bugs, and made 8 significant architecture decisions. Here's the specific evidence..."

2. Job Interviews

When asked "Tell me about a challenging technical decision," she references specific journal entries about the database schema choice, complete with the reasoning and trade-offs discussed.

3. Conference Talks

She submits a talk proposal: "The Hidden Complexity of Global Merchant Onboarding" based on her journal entries, with real data about the 200+ edge cases encountered.

4. Knowledge Transfer

New team members read relevant journal sections to understand why systems were built certain ways. "Bonnie, why did you use JSONB here?" "Let me show you the journal entry from when we made that decision..."

5. Blog Posts

Bonnie becomes known as a great technical writer, publishing monthly posts derived from her journal entries. Her posts get shared widely because they include real struggles and decision-making context.


Bonnie's Final Reflection (After One Year):

"This tool changed how I work. I'm more intentional about my decisions because I know they'll be documented. I commit more frequently because each commit tells part of the story. Most importantly, I've recovered the narrative thread of my career. When people ask what I've been working on, I don't just remember the last sprint - I can tell them the entire story of how we built our merchant platform, including all the dead ends and breakthroughs.

"The best part? Six months from now, when someone asks 'Why did we implement merchant validation this way?' - I won't have to guess. I'll have the exact conversation we had, the alternatives we considered, and the specific reasons we chose this path.

"It's not just a tool - it's like having a perfect memory of your engineering journey."

The Broader Impact

Bonnie's team adopts the tool after seeing her success. During retrospectives, they reference journal entries to identify patterns. During P0 incidents, they quickly find relevant past decisions. During architecture reviews, they cite specific journal entries as supporting evidence.

The journal entries become part of the company's institutional knowledge. As people leave and join, the stories stay. The context remains. The engineering narrative continues.