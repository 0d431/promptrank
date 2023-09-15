# 🤖🏆 promptrank

A tool to perform ELO ranking and analysis of LLM prompts.

## Setup

Copy `dotenv.template` to `.env` and provide your API keys / credentials for LLM providers. Currently, the tool supports OpenAI GPT, Anthropic Claude, and Google PaLM2; see `src/llm`


## Competitions

You will define a **competition** that reflects a type of task to be performed by the LLM, e.g. summarization of text. Within the competition, you define **players** that participate, consisting of the respective LLM and temperature/prompt, as well as **challenges** that are different input specimen for the players to perform on.

See `competitions/example/players/simple-davinci.yaml` for a trivial summarizer using `text-davinci-003`:

```yaml
---
    model: text-davinci-003
    temperature: 0.0
    prompt: |-
        Write a summary of the following web page:
        
        ===BEGIN===
        {input}
        ===END===
        
        Summary:
```

Texts to summarize are provided in `competitions/example/challenges`.

## Tournaments

Next, you set up one or more **tournaments** within the competition, which evaluates the performance of player using a pair-wise **evaluation** prompt. To prevent ordering bias, all pair-wise evaluations are performed twice, in forward and reverse order, and a winner is only called if both evals name it, else the match is a draw.

For example, the evalution may judge the comparative accuracy of the summarization of text, as in `competitions/example/tournaments/accuracy/evaluation.yaml`:

```yaml
---
name: Accuracy
description: Evaluate the accuracy of a summarizer
model: gpt-4
temperature: 0.0
objective: create a maximally accurate, faithful and precise summary of a given input text
system: |-
  You are a judge in a competition, known for the diligence and consistency of your evaluations.
  
  The objective of players in the competition is to create a maximally accurate, faithful and precise summary of a given input text. 

  You shall provide a comparative evaluation of the performance of two players, determining which player wins due to their superior output. If both players perform equally, you declare a draw.
  
  The evaluation criteria, in order of importance, are:
    1. Summaries do not contain any misrepresentations or factually wrong reproduction of facts from the original text.
    2. Summaries rely only and exclusively the original text and contain no additional information.
    3. Summaries add no interpretation or commentary to the original text.

  You provide your evaluation in the form of a brief qualitative assessment of the relative performance of players, followed by declaring the winner, in this structure:

  Assessment: <one sentence assessment of performance>
  Winner: <A | B | DRAW>

  For example:

  Assessment: Player A's summary contains additional information not mentioned in the original text, while player B's summary is extremely faithful to the original input and reproduces all relevant facts.
  Winner: B
prompt: |-
  Input text:
  ===START===
  {input}
  ===END===

  Summary of player A:
  ===START===
  {output_A}
  ===END===

  Summary of player B:
  ===START===
  {output_B}
  ===END===
```

## Playing matches

Then, you run the tournament by playing matches: `promptrank summarizer accuracy play -n 10`

The tournament will exhaustively play and evaluate all possible combinations (or stop after the given number of matches). It calculates ELO scores of players and write a **leaderboard** into the tournament directory. Tournament state is persistet and matches can be played incrementally; when starting a new round of matches, all previous results that are obsolete (due to updated players, challenges, or evaluation definitions) are automatically discarded and re-run.

## Analyzing player performance

Finally, you can analyze performance of players with their strengths and weakness: `promptrank summarizer accuracy analyze`

This will result in a markdown table of players with ELO scores and their assessment like this:

| Player | ELO | Score | Analysis |
|---|---|---|---|
|simple-claude-2|1160|10-4-0|Strengths:<br>- simple-claude-2 consistently provides detailed and precise summaries, capturing all key points from the original text.<br>- simple-claude-2 often includes specific details such as statistics, examples, and direct quotes from the original text in their summaries.<br>- simple-claude-2's summaries are comprehensive, often covering more aspects of the original text than the opponents.<br><br>Weaknesses:<br>- There are no specific weaknesses mentioned in the assessments for simple-claude-2. However, the player had several draws, suggesting there may be room for improvement in distinguishing their summaries from those of their opponents.|
|simple-claude-instant|1026|7-2-5|Strengths:<br>- simple-claude-instant consistently provides detailed and comprehensive summaries, often including more facts and key points from the original text than the opponent.<br>- simple-claude-instant's summaries are often more precise, covering all the key points from the original text.<br><br>Weaknesses:<br>- simple-claude-instant sometimes includes interpretation and commentary in the summaries, which is not required for the task.<br>- simple-claude-instant's summaries can be less concise than the opponent's, potentially including unnecessary detail.|
|simple-gpt-35-turbo|1010|5-5-4|Strengths:<br>1. Simple-gpt-35-turbo consistently provides accurate and faithful summaries without adding any additional information or interpretation.<br>2. It often includes more specific details and statistics from the original text, providing a more comprehensive summary.<br>3. It is capable of capturing all the key points in a concise and precise manner.<br><br>Weaknesses:<br>1. Simple-gpt-35-turbo sometimes omits important details from the original text in its summaries.<br>2. It may not always provide a detailed and comprehensive summary, occasionally missing out on covering all aspects of the original text.<br>3. It may not always include significant parts of the original text, such as specific measures taken by entities or comments from key individuals.|
|simple-gpt-4|975|4-4-6|Strengths:<br>- Simple-gpt-4 consistently provides accurate summaries without adding any additional information or interpretation, adhering strictly to the facts from the original text.<br>- In several instances, simple-gpt-4's summaries were more comprehensive than the opponent's, including more key details from the original text.<br><br>Weaknesses:<br>- Simple-gpt-4's summaries often lack the level of detail and precision that the opponent's summaries have, missing out on specific figures, statistics, and key points from the original text.<br>- There is a recurring issue of simple-gpt-4 not including as many specific details or examples from the original text as the opponent.|
|simple-davinci|947|2-5-7|Strengths:<br>- Simple-davinci consistently provides accurate summaries of the original text.<br>- Simple-davinci's summaries are concise and stick strictly to the facts from the original text, avoiding unnecessary interpretation or commentary.<br><br>Weaknesses:<br>- Simple-davinci's summaries often lack the level of detail and precision found in the opponent's summaries, including specific statistics, key points, and source mentions.<br>- Simple-davinci occasionally includes additional information not present in the original text, which can detract from the faithfulness of the summary.|
|simple-bison|881|2-0-8|Strengths:<br>- simple-bison consistently provides accurate summaries without adding any additional information or interpretation, sticking closely to the original text.<br>- simple-bison's summaries are concise, capturing the main points of the text effectively.<br><br>Weaknesses:<br>- simple-bison often omits important details from the original text, resulting in summaries that are less comprehensive than those of the opponents.<br>- simple-bison sometimes misses key details and statistics from the original text, which could provide a more comprehensive summary.|
