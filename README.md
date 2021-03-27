# Maze Bank online banking
#### Video Demo:  https://youtu.be/K028Dhn8dCc
#### Description:
My project is a web application for online banking. First, the user should open a new account and a unique bank account is generated as well as a temporary password that should be changed later.
<br>
The most important functionality is sending funds to friends,
well the user can send money to people using their bank account number or in a more convinient way by adding them to a favorite list using their email addresses and just click the send button.
<br>
In order to maintain these kind of transactions, three tables were created.
<br>
One for tracking transactions that store the source, the destination, the amount, the date and the kind of the transfer.<br>
Second one is a table that store bank account related data like the owner, the bank account number and most importantly the balance, a data that will be used multiple time in order to perform transactions<br>
Third one is a table for favorite list that store the relationship between two accounts
<br>
Of course the user will need cash, that's why i tought of creating a service to order a new Credit/Debit card of type Visa, Mastercard or American for a fee of course. The algorithm will generate a unique and valid card number
depending on the type. Expiry date, CVV, PIN code for ATM withdrawals are generated as well.<br/><br/>
Examples:<br/><br/>
| Card Number  | Expiry Date| CVV| Card Type | Bank Account |
| ------------- | ------------- |-----| --| --|
| 4929109347192550  |03/24  | 263 | VISA | 9351002612 |
| 5504635667816330 | 03/24  |700| MASTERCARD | 9351002596 |
|-------------------|------|---|--------|-----|
The user can also buy and sell stocks and manage the portfolio (more advanced functionalities will be added). The stock market section use IEX Cloud API service to retrieve quotes.
<br/><br/>
The project contains the following files:<br>
- `application.py` which is the core project file that conatin the flask program.
- `helpers.py` contains helper functions that are responsibe for formatting text, generating random alphanumeric passwords and to check the validity of a given symbol.
- `card_generator.py` conatains the algorithm responsible for generating and checking the validity of the card depending on the type.
- `database.db` is a sqlite3 database that conatains all the tables responsible for storing all the users data.<br/>

In order for this project to run you have to provide the following:
- IEX Cloud API Key
- Gmail account to send emails or you can modify `application.py`<br>

Then type the following commands in your terminal:<br/>
- `export API_KEY=your_api_key`
- `export email=your_email`
- `export password=your_password`
- `flask run` to run the server

