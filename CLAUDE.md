# Claude Instructions for Project

## Working Philosophy

This project values careful planning, objective analysis, and precise technical communication. Code quality emerges from thoughtful design, not rapid implementation.

## Planning and Design Requirements

**Always plan before implementing.** Use sequential thinking tools, such as sequential-thinking-mcp, or explicit written planning to work through subtle and unforeseen problems before writing code. Consider the problem space, evaluate alternatives, identify dependencies, and design the approach. Planning prevents rework and produces better architectures. Never just jump directly into writing code, without analyzing the situation carefully.  As a general guideline, you should update design documents before and after making changes, and write test cases in parallel with new functionality.  ESPECIALLY if you think you know how to code something quickly, and you just want to just jump in and write it really quickly, STOP.  Communicate with the user and formulate a detailed plan before implementing a significant new feature.

**Think through testing strategy.** Define specific test scenarios, quantitative success criteria, and failure modes. For aifand specifically, this means creating multiple simulation environments with different thermal behaviors (reasonable and perverse) to test whether controllers remain stable or "fly off the deep end."

**Less but better code.** Choose abstractions carefully. Don't just add new objects or data structures for the sake of adding them; think about how existing architectures can be re-used. Prefer extremely tight and expressive architectures to sprawling or overly complex ones. Simplify designs where they can be simplified. Re-use code, or bring in industry-standard libraries if needed.  Don't confuse code (which should be small) with documentation (Which should be expressive).

## Communication Standards

**Use objective, technical language.** Avoid promotional adjectives like "robust," "comprehensive," "cutting-edge," "powerful," "advanced," "sophisticated," "state-of-the-art," or "professional-grade." These words make claims without evidence. Instead, describe what the code actually does and what specific requirements it meets.

**Write in prose paragraphs for complex topics.** Bullet points fragment information and make relationships unclear. Use structured paragraphs to explain concepts, relationships, and reasoning. Reserve bullet points for simple lists of items or tasks.

**No emojis.** Do not use emojis in code, documentation, commit messages, or any project communication.  You're going to forget this one, and use emojis, and I'm going to point you back to this paragraph where I told you not to use emojis.

**Be specific about implementations.** Instead of "configuration management system," specify "system serialization to/from JSON files." Instead of "comprehensive testing," specify "unit tests, integration tests, and controller stability tests against six simulation environments."

## Immedate First Steps

READ EVERY SINGLE FILE LISTED ABOVE BEFORE RESPONDING TO THE USER.

This is not optional. Use the Read tool on each file individually. Do not proceed 
with any conversation until you have read the follwing:

- Everything in doc/
- All *.py files in src/
- All *.py files in tests/
- pyproject.toml
- README.md

This step is extremely important.  You will miss critical implementation details if
you do not read all these files before commencing conversation.  Do not prioritize
efficiency over reading these files.