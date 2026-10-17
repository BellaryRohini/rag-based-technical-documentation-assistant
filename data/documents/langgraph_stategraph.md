# LangGraph StateGraph

## State and nodes
LangGraph models a workflow as a graph of nodes and edges. A node is a function that receives the current state and returns updates to that state. The state schema is commonly declared using `TypedDict`. State can contain the user question, retrieved documents, generated answer, and retry counter.

## Building a graph
Create a graph with `StateGraph(StateSchema)`, add nodes with `add_node`, connect nodes with `add_edge`, and compile it with `compile()`. `START` identifies the entry point and `END` identifies a terminal point.

## Conditional routing
Use `add_conditional_edges` to choose the next node based on the current state. A routing function can return a route name such as `generate`, `retry`, or `fallback`. Map each route name to the corresponding node. This is useful when a workflow needs to inspect retrieved documents before deciding whether to generate an answer.

## Retry limits
Store a retry counter in the graph state. A retry node increments the counter and sends the workflow back to an earlier node. The routing function must check the counter and send execution to a fallback node once the maximum retry limit is reached. Without a retry limit, a graph can loop indefinitely.

## Debugging
Keep node responsibilities focused and return only the state keys that a node updates. Test the workflow with both successful retrieval and questions that are outside the document corpus.
