'''
Define the graph state
We now define the graph state. The state for the traditional LangChain agent has a few attributes：
1. input: This is the input string representing the main ask from the user, passed in as input.
2. Chat_history : This is any previous conversation messages, also passed in as input.
3. intermediate_steps : This is list of actions and corresponding observations that the agent takes over time. This is updated each iteration of the agent.
4. agent_outcome : This is the response from the agent, either an AgentAction or AgentFinish. The AgentExecutor should finish when this is an AgentFinish,
otherwise it should call the requested tools.
'''
import operator
from langchain_core.agents import AgentAction,AgentFinish
from langchain_core.messages import BaseMessage
from typing import TypedDict,Annotated,List,Union

class AgentState:
    input:str
    chat_history:list[BaseMessage]
    # The outcome of a given call to the agent
    # Needs 'None' as a valid type, since this is what this will start as
    agent_outcome = Union[AgentAction,AgentFinish,None]
    # List of actions and corresponding observations
    # Here we annotate this with 'operator.add' to indicate that operations to
    # this state should be ADDED to the existing values (not overwrite it)
    intermediate_steps:Annotated[list[tuple[AgentAction,str]],operator.add]



