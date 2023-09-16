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

Finally, you can analyze performance of players with their strengths and weakness: `promptrank summarizer accuracy analyze -w`

This will result in a markdown file `analysis.md` in the tourname directory (omit `-w` to get markdown to console):

6 players, 3 challenges, 45 out of 45 matches played

| Player | ELO | Score | Analysis |
|---|---|---|---|
**simple-claude-2**|1121|8-6-0|Simple-claude-2 consistently excels in creating comprehensive, detailed, and precise summaries that capture all key points from the original text without adding any additional information or interpretation.<br><br>Weaknesses:<br>- The assessments do not indicate any weaknesses in simple-claude-2's performance, as all the feedback is positive and the remaining matches were draws, suggesting that simple-claude-2's performance was on par with the opponents'.<br>- There is no mention of simple-claude-2's ability to summarize texts of varying complexity, length, or subject matter, which could potentially be a limitation.<br>- The assessments do not provide any insight into simple-claude-2's speed in generating summaries, which could be a potential area for improvement in a competitive setting.|
**simple-claude-instant**|1070|7-5-2|Simple-claude-instant's key strength is their ability to provide detailed and comprehensive summaries that include all key points and facts from the original text.<br><br>Weaknesses:<br>- While the player's summaries are detailed, they may sometimes lack conciseness and precision, which can make them longer and potentially harder to digest than necessary.<br>- The player may occasionally omit important details, such as the potential for further rate increases and the views of policymakers, which can affect the accuracy and completeness of the summary.<br>- The player's focus on detail may sometimes lead to overemphasis on certain points, potentially causing an imbalance in the representation of the original text's content.|
**simple-gpt-4**|995|3-7-4|Simple-gpt-4's key strength is its ability to provide accurate summaries that often include specific data and comprehensive details from the original text.<br><br>Weaknesses:<br>- Simple-gpt-4 occasionally omits important details from the original text, such as potential future events or the views of key individuals, which can reduce the completeness of its summaries.<br>- Compared to its opponents, simple-gpt-4's summaries are sometimes less detailed, missing out on some facts from the original text.<br>- There is a recurring issue of simple-gpt-4's summaries lacking in precision and detail, which suggests a need for improvement in capturing more key points from the original text.|
**simple-gpt-35-turbo**|981|3-7-4|The player simple-gpt-35-turbo demonstrates a strength in creating concise, precise summaries that often include important additional details such as sources and public expectations.<br><br>Weaknesses of the player include:<br>- The player occasionally omits important details from the original text, such as specific actions of major supermarkets, potential interest rate rises, and comments from policymakers.<br>- While the player's summaries are often concise, this sometimes comes at the expense of comprehensiveness, with the opponent's summaries frequently including more facts from the original text.<br>- The player's performance is inconsistent, with several draws indicating that while the player can produce accurate summaries, they do not consistently outperform their opponents.|
**simple-davinci**|980|2-7-5|Simple-davinci's key strength lies in its ability to provide concise, precise, and accurate summaries without adding any additional information or interpretation.<br><br>Weaknesses:<br>- Simple-davinci often omits important details from the original text, such as specific data points or key aspects, which can lead to a less comprehensive summary.<br>- While the player's summaries are concise, they sometimes lack the necessary detail and precision, resulting in a summary that does not fully capture all the key points from the original text.<br>- Simple-davinci's performance is inconsistent, with some summaries being more comprehensive and detailed than others, indicating a potential issue with the player's ability to consistently identify and include all relevant information from the original text.|
**simple-bison**|850|0-2-8|Simple-bison's key strength is their ability to provide accurate and concise summaries without adding any additional information or interpretation.<br><br>Weaknesses:<br>- Lack of comprehensiveness: Simple-bison often omits important details from the original text, such as the impact of the cost-of-living crisis on partnerships, the role of AI, and the most admired partnerships.<br>- Incomplete coverage of key points: Simple-bison's summaries often lack key points from the original text, such as the retailers' responses to the crisis, the research by BritainThinks, and consumers' expectations from retailers.<br>- Insufficient inclusion of source and context: Simple-bison's summaries often fail to include important contextual information such as the source of the research and the public's expectations of retailers' responses to the crisis.|


### ELO score development
![ELO Development](./competitions/example/tournaments/accuracy/elo_history.png)