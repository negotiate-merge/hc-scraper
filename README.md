# Hot Copper - Forum post web scraper by user

## To Do list
- COMPLETED Rewrite find_posts so that it uses accurate datetime objects.
- PARTIALLY COMPLETED - CHECK FOR BEHAVIOUR ON RERUNS FROM ONETIME Save the json output for each year so that it can be fed in to other systems (LLM)
- If the posts returned is equal to one maybe we should check to see if this is an error resulting from not being logged in.
  Would have to figure out how to test for valid session.
- Incorporate a better form of logging so that edge case errors are easier to pin point and rectify. 
  We want to know exactly where the scraper crashed so we can recommence from that point when the fix is made.
- I have a feeling that despite my best efforts, I may have duplicate links and duplicate data.. looking at the json for 2024, there are entrys in there from 2023. Need to properly define what constitutes a thread belonging to a certain year. Is it when the thread was created or when the latest user post was? Latest post is a changing thing if you want to work on data already collected it would require alot of processing. date of creation is probably the best option here. Everything is fixed in time that way.

## Nice to have in the future
- Redo get_user_posts json entrys could be updated in place.
- makeHTML should create a new file regardless of a file existing with the same name. We have changed the program to write all years data to json so we are not reusing the json file for each year anymore.