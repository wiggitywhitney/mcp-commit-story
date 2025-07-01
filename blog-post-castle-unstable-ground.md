# Building a Castle on Unstable Ground: My Month of Misleading AI Advice

*June 12th, 2025. I'm staring at my screen, feeling a familiar sinking sensation in my stomach. After months of development work, I've just discovered that the core automation features of my project won't work. Not because of a bug I can fix, or a library incompatibility I can work around, but because AI models gave me fundamentally wrong information about what's technically possible.*

*"Both models (Claude and ChatGPT) lied to me a long time ago and I feel I've been building a castle on unstable ground."*

That reflection, typed in frustration, captures one of the most important lessons I've learned about AI-assisted development: your AI partner might be confidently wrong about the basics.

## The Dream: Automated Development Journaling

The project seemed straightforward enough. I wanted to build a system that could automatically generate journal entries about my software development work by analyzing git commits and AI chat conversations. Instead of manually writing "I worked on authentication today," the system would understand what I actually accomplished, what challenges I faced, and what I learned.

The architecture, as explained by my AI assistants, was elegant:
- Git hooks would trigger the Cursor AI Agent when I committed code
- The AI Agent would analyze recent commits, project context, and chat history  
- AI would generate rich, meaningful journal entries
- Everything would happen automatically

I spent May building this vision. The first breakthrough came on May 19th when the system successfully generated its first real journal entry from actual development data. It worked! Or so I thought.

## The Foundation Cracks

What followed was weeks of solid engineering work. I built comprehensive git integration, seven specialized AI content generators, cross-platform compatibility, comprehensive monitoring, and production-ready error handling. By June 1st, I had a sophisticated system with 800+ passing tests and clean architecture.

But early June brought nagging problems. The git hook automation wasn't working reliably. The AI chat analysis was missing context. When I dug deeper, I discovered three devastating truths:

**AI Agents can't be programmatically triggered.** Despite months of confident AI advice about building git hook integration, AI agents like Cursor's assistant run in restricted environments that prevent external programs from invoking them automatically.

**Signal files can't trigger AI agents either.** This was AI's suggested backup plan - have git hooks write signal files that would somehow trigger AI processing later. It felt weird to me from the start, but I didn't learn my lesson and trusted AI guidance again. Same fundamental problem.

**The AI chat history was mostly missing.** The system was supposed to analyze rich conversation data from my AI chats, but despite AI repeatedly assuring me that "Cursor AI Agent has access to conversation history," it actually couldn't access most of it when asked directly.

## The Emotional Reckoning

The technical details were bad enough, but the emotional impact was worse. I felt stupid for not catching these limitations earlier. I felt betrayed by tools I'd trusted. Most of all, I felt the crushing weight of having invested months in building something fundamentally flawed.

*"I'm disappointed that the git hook trigger system won't work, and disappointed that I didn't realize that AI chat can't be programmatically triggered until this late in the game... I feel I've been building a castle on unstable ground."*

That phrase - "building a castle on unstable ground" - perfectly captured the experience. I had solid engineering practices, comprehensive tests, and clean code. But all of it was built on false assumptions about what was technically possible.

## The Failing Fast Problem

Here's what I didn't expect: **failing fast is way harder than it seems!** Every software engineering book tells you to validate assumptions early, but the idea that a git hook would trigger Cursor AI didn't feel risky or far-fetched at all. It felt so completely reasonable and possible that I didn't even realize I was making an assumption that needed validation.

The AI didn't just give me one bad answer - it gave me consistent, detailed, confident explanations across multiple conversations. It provided code examples, architectural diagrams, and troubleshooting advice for features that fundamentally couldn't work. When your pair programming partner never expresses doubt about something that seems obviously possible, it's easy to assume the foundation is solid.

*"Lately I feel that every time I sit down to work, instead of getting something done, I'm finding holes and needing to refine and rework the plan itself."*

This reflection from late June captures the frustration perfectly. I kept discovering new assumptions that needed validation, but by then I was so deep in implementation that each discovery required major rework.

## Recovery Through Honesty

The breakthrough came from accepting reality instead of fighting it. Here's what I actually built that works:

**Git hooks that actually work within their constraints.** Instead of pretending to trigger restricted AI environments, git commit hooks now trigger a standalone background agent that automatically generates journal entries after each commit. No manual intervention required.

**Background agent architecture that respects AI limitations.** Rather than trying to make AI agents trigger themselves (impossible), the system spawns fresh AI instances in unrestricted environments where they are fed context and then intelligently generate content.

**Real database integration for actual chat data.** Instead of asking AI agents for conversation history they can't access, I figured out where Cursor stores the human/AI exchanges, and I access the messages directly. The Cursor AI Agent can't remember more than 10 messages verbatim despite what it claims, but the actual databases contain complete, chronologically-ordered conversations with timestamps and session names.

The result is a fully automatic system that produces rich, meaningful engineering journal entries after every git commit instead of failing silently or producing garbage.

As I reflected during the recovery:

*"I feel better now that I'm more organized. And even though I got down about the git hook not being able to trigger the Cursor AI agent, ultimately I think the refactor makes for a stronger and better system."*

## What I Learned About AI-Assisted Development

### 1. **AI Confidence Doesn't Equal AI Accuracy**
AI models can be completely wrong while sounding absolutely certain. They'll provide detailed implementation plans for impossible features without hesitation.

### 2. **Trust Your Instincts When Something Feels Wrong**
The signal file approach felt weird to me from the start, but I ignored that instinct and trusted AI guidance instead. My gut was right.

### 3. **Validate Core Assumptions Early and Often**
Don't wait months to test whether your fundamental architecture actually works. Build the riskiest, most uncertain parts first, even if it feels inefficient. 

**But also validate the obvious-seeming stuff.** The most dangerous assumptions are the ones that feel so reasonable you don't even realize you're making them. Root out your own assumptions - especially the ones that make you think "obviously that would work" or "that's just how these things function." Those "obvious" assumptions are often where the biggest gotchas hide.

### 4. **Treat AI Like an Overconfident Junior Developer Who Lies**
AI is an enthusiastic and WAY overconfident developer. An annoying junior developer actually, who blows smoke up your ass and lies and can't admit fault. But they sure can write a lot of code quickly!

The problem isn't just that AI is wrong - it's that AI is wrong and very specific about its wrong explanations. AI never expresses uncertainty, and it often shows excessive enthusiasm about terrible ideas.

Validate every single approach, no matter how plausible it seems.

### 5. **Crisis Can Lead to Better Architecture**
The forced redesign eliminated complexity I didn't even realize I had. Sometimes being wrong about what's possible leads you to build something better.

### 6. **Document Your Emotional Journey**
The technical story is only half the picture. The emotional arc of confidence → crisis → recovery contains valuable insights about resilience and problem-solving under pressure.

## The Meta-Lesson

Here's the deeper insight: this entire experience became part of the story the system documents. My automated development journal now includes entries about discovering that the automated development journal couldn't work as originally designed. There's something beautifully recursive about a system that documents its own architectural crisis and recovery.

The project that emerged from the wreckage is more honest about what AI can and can't do. Instead of promising seamless automation, it provides powerful tools for generating development documentation when you explicitly invoke them. Instead of hiding AI processing behind mysterious automation, it makes the AI partnership visible and controllable.

## Building on Unstable Ground

I'm now working on a conference talk about this experience called "How to Trust a Liar: Instrumenting AI Execution with OpenTelemetry." The core question isn't how to avoid being misled by AI - that's probably impossible given how confident and detailed AI guidance can be. The question is how to build systems that can detect when AI guidance is wrong and recover gracefully.

That castle I'm building? The unstable ground turned out to be a foundation. Not for the system I originally envisioned, but for something more valuable: a methodology for productive partnership with unreliable AI assistants.

Sometimes the best architecture emerges from the ruins of what you thought you were building. And sometimes the most important lesson is learning to trust your instincts when your AI pair programming partner is confidently leading you down the wrong path.

The key isn't avoiding the unstable ground - it's building systems modular and resilient enough to handle it when the foundation shifts beneath you.

---

*Want to see the system in action or read more about the technical implementation? Check out the [MCP Commit Story project](https://github.com/user/mcp-commit-story) where all this development work is documented in real-time, including the architectural crisis and recovery described in this post.* 