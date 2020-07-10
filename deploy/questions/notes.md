# Notes on Experiments
I've taken the questions that Jasenka made before, and am running them against the current server.  There are 2 "stages" as of right now.  In the first stage, I just run the whole question set against the server and record the results.  I then go to the results and try to find examples of how well the questions were answered and identify potential problems and solutions.  In the second stage I run queries against the server and try to tweak the index to perform better.  

This stage consists of roughly the following workflow:
* identify a question that was answered poorly
* run the query and view the _explain log_ to see what document were retrieve by the index and why
* run different models against the query and relevant documents to see how they perform in comparison to the one currently being used
* tweak the stopwords and synonyms file to try to better map queries to documents
* edit the documents in the index if appropriate
* restart the server (implicitly, reindex the collection)
* repeat the process

This can be seen as a "fine tuning" stage.  In the first instantiation of the workflow, here is what I've observed:
* the standard bert model tends to perform better
* synonyms can be used as a cheap way of "intent recognition" and serve to create latent representations of queries
* editing the documents can lead to much better results
* some questions just won't be easily answered by the model

## Different Models
The standard bert model 'twmkn9/bert-base-uncased-squad2' seems to be able to answer questions better than the distilbert model being used before.  This is no surprise, however it should be noted that there are certain cases where distilbert does a better job than bert.  This primarily occurs when there isn't really a good answer in the context, but bert manages to find one anyways.  They both perform better than the distilbert model trained on only squad:  'distilbert-base-uncased-distilled-squad', and the performance of the small-bert model seems to slightly worse than distilbert, however it is the case that it sometimes gets a good answer when distilbert does not.  I've decided to switch to the standard bert model for further testing.

## Synonyms as Latent Variables
Given that we have a fairly small collection, and we are trying to keep our documents (paragraphs) small, there is a good chance that many queries will not match to the correct documents.  While approaches such as word-vectors to do similarity scoring may be more robust, synonyms are a cheap and simple way to achieve similar results.  The three main components of the text analysis that occurs on the index are synonym-expansion, stopword removal, and stemming.  The three of these combined seem to do a decent job of matching queries to documents.

Some of the synonyms are clear, such as "use, work with, utilize," some of them are domain-specific, such as "ai, machine learning, artificial intelligence" and "software, program, solution," and some aren't really synonyms.  For example: "products, services, expertise, specialty" are mapped to a synonym, while they aren't necessarily synonyms.  In our case, while their meanings aren't synonymous, in the context of a query about mono they are likely to have similar semantic meaning, and the documents properly answering these queries are likely to be identified with any of the words in the set.

It's worth mentioning that typical complaints about synonyms are categorically not a problem for us.  Many will say that using synonyms can be a problem when the relevance of documents is not clear to a user.  In our case, these documents are hidden from the user.  To our model, if a document truly is irrelevant, then it should simply find no answer to the question posed (this is the advantage to using models trained with SQuAD-2).  The models tend to do a pretty good job identifying when an answer is not present.  In fact, it seems that they may be well served by domain-specific fine tuning.  For example, while we are identifying "app" and "solution" as having similar semantic content, it is possible that the models will not recognize this.  Fine-tuning will be a good next step after doing a reasonable amount of editing/ tweaking the index.

## Editing Documents and Writing Style
In some cases it was useful to further split documents into smaller pieces.  It was observed that in some cases an answer was clearly present, but the model would converge on no answer, likely due to an inability to properly divide its attention among the relevant parts of the context.  When a document is split, it's important to make sure that referents are "closed."  For example, if the sentence "John works at mono.  He likes javascript" were to be split into two separate contexts, the pronoun "He" should be transformed into "John" (the model will have no way of knowing that "he" refers to "John").  This leads to the problem of writing style, for which a solution is not really clear to me.  On the one hand, one might say that we are trying to use models that do not depend on highly structured text to answer questions.  In this case, there seems to be a strong argument that the source documents should be edited as little as possible, that they should be able to read whatever was written under natural conditions and its performance then judged.  On the other hand, one could also say that we are trying to build a well-performing question-answering system with a controlled source of knowledge.  In this case, it seems clear that choosing a writing style that ensures best performance by the model is a priority.  The final answer likely lies somewhere in the middle, so here are a few observations of writing style that seem to be making things more difficult for the model:

### Lists
As mentioned before, lists seem to give the model a hard time.  This is likely because the lists contain a large amount of potentially relevant words, and the model has to keep attention on different parts of (perhaps all of) the list.  As a rough demonstration of this, go to [hugginface-exbert](https://huggingface.co/exbert/?model=distilbert-base-uncased&modelKind=bidirectional&sentence=We%20use%20all%20of%20the%20following%20tools:%20python,%20javascript,%20dotnet,%20computers,%20embedded%20systems,%20angular%20-%20anything%20you%20can%20think%20of!&layer=0&heads=..&threshold=1&tokenInd=22&tokenSide=right&maskInds=..&hideClsSep=true), click "Unselect all heads," set the slider to "sho top 100% of att," and click on the word "use".  No hover your mouse over the different layers of the model to get an idea of how the attention is being distributed at different "heads."  This list example is good, because it is not exactly clear what the solution is.  It would not be appropriate to write out "we use x. we use y.  we use z."  But it does strain the model.  I think that if it becomes a serious problem we need to solve, we should use some sort of intent-recognition to do it (for example, recognize the intent: list all languages used).

### Prices
This is a somewhat similar problem to lists.  The best answers from the model with regard to pricing are "salesman bullshit."  Here is a concrete example from the test I just ran:

* question - I want to create a mobile app, how much does it cost?
* answer - Our mobile app projects share great amounts of code between platforms, enabling us to deliver mobile solutions at a fraction of the time and cost needed to build separate versions for each platform.

From the point of view of trying to make a nice bot that answers reasonably well, this is perfectly acceptable.  If I were a customer, this might be a little annoying though.  Furthermore, none of the following questions were able to be answered by the model:

* How expensive is your custom made software?
* What are the hourly rates in Mono?
* What is your hourly rate?
* I want to create a new website for my business, how much does it cost?
* How much Baasic costs?
* Is eCTD Office free?
* How much eCTD Office costs?

Of course, it is quite likely that the answers to these questions don't really lie within the source documents, but still it seems like it would be pretty easy to identify if someone were trying to learn about prices and redirect them accordingly.  This may be an interesting application of the word/sentence embeddings, but even just some regular-expression matching could probably do a decent job of identifying this intent.

### First, Second, and Third Person Perspectives
This is actually a very serious issue, and one that will have to be addressed in a principled way for dealing with the service.  When a query contains the term "you," are they referring to Mono, the bot, or a person who represents Mono?  Here is a good example, taken from [the website](https://mono.software/technologies/mobile/):

> Mono development team can build mobile apps for every platform and purpose, using a wide array of cross-platform tools.
> We have started building mobile apps for iOS and Android platform using native development tools (Objective-C and Swift for iOS and Java for Android). 

Here are some somewhat convoluted questions to illustrate the problem: "do you use cross-platform tools?", "does Mono build apps for Android?"  In the first case, the model must identify that "you" refers to "Mono," and in the second that "Mono" refers to "we."  In some cases, the model does this quite well, probably on accident, and in some obvious cases it fails.  I think the easiest solution would be to map queries like "you -> Mono", then in the source map "we -> Mono", then in the answer map "Mono -> we."  It would probably do okay, but there are probably a number of places where it doesn't make sense (and violates grammar).

## Bad Questions for the Model
I took the questions directly from what Jasenka made before, so there are probably a number of questions which simply can't be answered by the associated knowledgebase.  Like I mentioned before, there are lists and asking for prices are also in the realm of "unanswerable questions."  Yes or no questions are also not answered directly, we can pursue detecting these cases individually but returning a complete sentence like we're doing now isn't completely unreasonable.

## Overall Results
Out of 131 question, the model answered 72.  I gave each question and answer a (subjective) grade as follows:
* 2: good
* 1: okay
* 0: bad
* -1: irrelevant/ meaningless

With this system, the scores turned out like:

  | q | a |
-1| 0 | 9 |
 0| 3 | 9 |
 1|19 |28 |
 2|50 |26 |

Some of the questions got bad scores because they had bad grammar or were poorly worded, and questions about prices generally were given lower scores.
Other relavant statistics include how many of the files were actually used in answering some question.  Of the 62 files, 33 were used.  The listing of which files were used or not is in the file "used\_source\_docs.txt"  Examining the type of information not being yet utilized and why will be done tomorrow.
