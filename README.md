# Zero Sum Fight Club

[![Buckshot Roulette](https://img.youtube.com/vi/H6rJNNFsRpY/0.jpg)](https://www.youtube.com/watch?v=H6rJNNFsRpY)

I recently stumbled across [this](https://www.youtube.com/watch?v=H6rJNNFsRpY)
video where someone was using a game called Buckshot Roulette to test out 
GPT-5's ability to reason. They were doing this by manually sending the rules
to ChatGPT then going through a loop of prompting it for a move, sending 
the feedback and then prompting for another move. At some point they said this
would be much better if someone could automate it.

The plan for this repo is to create a test harness for simple two-player games
like this so that I can test out various AIs to see how they perform. The goal
is to eventually have something flexible enough to be able to swap out 
different games with their own rules, but to start off I will:
  * Recreate the Buckshot Roulette game in text form
  * Create an agent that performs random moves
  * Create an agent that uses ExpectiMax to pick the best moves
  * Get a baseline of how the random agent performs against the ExpectiMax 
    agent
  * Create an agent that uses GPT to pick moves
  * Experiment with different LLMs & prompts
