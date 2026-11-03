# Reflection

The project has three parts. `validation.py` holds the rules, `client.py` is the Tkinter form, and `server.py` is the Flask API. When the user clicks Submit, the form checks the input, converts it to JSON and POSTs it. The server checks the data again and returns a 201 or a 422 response, which the form then displays.

Two things surprised me. The first was how easily a price can go wrong. A float would turn 1000.00 into an approximation, so I switched to `Decimal` and send the price as a string. The second was that Tkinter isn't thread-safe. My first idea was to call `requests.post` straight from the button handler, but that would freeze the window. In the final version the request runs on a worker thread, and the result goes back to the window through `after()`.

My code changed when I realized the client and the server needed the same rules. Moving them into one shared module stopped the two from drifting apart. The client validates so the user gets quick feedback, and the server validates again because a client can't be trusted.

Next, I'd like to learn async GUI patterns and how to store data in a real database.
