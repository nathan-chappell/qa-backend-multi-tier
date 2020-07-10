# qa\_backend

This is the repo for the `qa_backend`.  To get running quickly, see the readme
in [deploy](./deploy).  Here the basic architecture will be explained.

## MainServer

The `MainServer` is the primary tool developed here.  It depends on
**servers** and **services**, as well as as configuration file.  The two
servers currently implemented are the `QAServer` and the `TransformersMicro`.
The services are of two varieties, **database** and **qa**.  The **database**
service must implement a _CRUD_ interface.  A `QueryDatabase` also must
implement a _query_ function, intended for something like elasticsearch.  A
**qa** service must implement a `query` method, which takes at least a
question.  Any **qa** service must also have a flag indicating if it requires
context to answer a question or not.
