import asyncio
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, render_template, jsonify, request, flash, redirect, url_for, abort
import datetime, requests
from datetime import datetime
import pymssql, shopify
import aiohttp
import lazop
import aiohttp

app = Flask(__name__)
app.debug = True
app.secret_key = os.getenv('APP_SECRET_KEY', 'default_secret_key')  # Use environment variable


def get_db_connection():
    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_DATABASE')
    username = os.getenv('DB_USERNAME')
    password = os.getenv('DB_PASSWORD')
    try:
        connection = pymssql.connect(server=server, user=username, password=password, database=database)
        return connection
    except pymssql.Error as e:
        print(f"Error connecting to the database: {str(e)}")
        return None



def check_database_connection():
    server = 'tickbags.database.windows.net'
    database = 'TickBags'
    username = 'tickbags_ltd'
    password = 'TB@2024!'

    try:
        print('Connecting to the database...')
        connection = pymssql.connect(server=server, user=username, password=password, database=database)

        print('Connected to the database')
        return connection
    except pymssql.Error as e:
        print(f"Error connecting to the database: {str(e)}")
        time.sleep(5)
        check_database_connection()
        return None


def fetch_transaction_data():
    connection = check_database_connection()
    if connection is None:
        return []
    print("CONNECTED TO DATABASE")

    try:
        with connection.cursor(as_dict=True) as cursor:
            query = '''SELECT * FROM IncomeExpenseTable ORDER BY "Payment_Date" desc'''
            cursor.execute(query)
            transactions = cursor.fetchall()
            return transactions
    except pymssql.Error as e:
        print(f"Error fetching data from the database: {str(e)}")
        return []
    finally:
        connection.close()


def format_date(date_str):
    # Parse the date string
    date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
    # Format the date object to only show the date
    return date_obj.strftime("%Y-%m-%d")


@app.route('/finance_report')
def finance_report():
    transactions = fetch_transaction_data()
    return render_template("finance_report.html", transactions=transactions, account=True)



def fetch_monthly_financial_data(connection):
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT Month, NetProfit FROM MonthlySummary ORDER BY Month ASC")
        financial_data = cursor.fetchall()

        formatted_data = {
            'months': [row[0] for row in financial_data],
            'net_amounts': [row[1] for row in financial_data]
        }

        return formatted_data

    except Exception as e:
        print(f"Error fetching monthly financial data: {str(e)}")
        return {'months': [], 'net_amounts': []}

    finally:
        cursor.close()


def fetch_account_summary(connection):
    cursor = connection.cursor()

    try:
        # Fetch Cash on Hand (assuming it's stored in the 'accounts' table)
        cursor.execute(
            "SELECT FORMAT(accounts_balance, 'N0') as FormattedAmount   FROM accounts WHERE accounts_name='Bank'")
        cash_on_hand = cursor.fetchone()[0]

        # Fetch Earnings (Monthly)
        cursor.execute("""
            SELECT FORMAT(Income, 'N0') as FormattedAmount
            FROM MonthlySummary
            WHERE [Month] = FORMAT(GETDATE(), 'yyyy-MM')
        """)
        earnings_monthly = cursor.fetchone()[0] or 0

        # Fetch Expenses (Monthly)
        cursor.execute("""
            SELECT FORMAT(Expense, 'N0') as FormattedAmount
            FROM MonthlySummary
            WHERE [Month] = FORMAT(GETDATE(), 'yyyy-MM')
        """)
        expenses_monthly = cursor.fetchone()[0] or 0

        # Calculate Net Profit (Including Withdrawal)
        cursor.execute("""
            SELECT FORMAT(NetProfit, 'N0') AS FormattedAmount
            FROM MonthlySummary
            WHERE [Month] = FORMAT(GETDATE(), 'yyyy-MM')
        """)
        net_profit = cursor.fetchone()[0] or 0

        return {
            'cash_on_hand': cash_on_hand,
            'earnings_monthly': earnings_monthly,
            'expenses_monthly': expenses_monthly,
            'net_profit': net_profit
        }

    except Exception as e:
        print(f"Error fetching account summary: {str(e)}")
        return {}

    finally:
        cursor.close()


def fetch_accounts_data(connection):
    cursor = connection.cursor()

    try:
        cursor.execute(
            'SELECT accounts_name, accounts_balance FROM accounts order by accounts_balance desc')  # Adjust the query accordingly
        accounts_data = cursor.fetchall()

        formatted_accounts = []

        for row in accounts_data:
            formatted_account = {
                'person_name': row[0],
                'balance': int(row[1]),

            }

            formatted_accounts.append(formatted_account)

        return formatted_accounts

    except Exception as e:
        print(f"Error fetching accounts data: {str(e)}")
        return []

    finally:
        cursor.close()


def fetch_income_list(connection):
    cursor = connection.cursor()

    try:
        # Execute the SQL query
        query = '''

SELECT TOP 5
    Income_Expense_Name,
    SUM(CAST(Amount AS FLOAT)) AS Amount
FROM IncomeExpenseTable
WHERE Type = 'Income'
    AND FORMAT(CONVERT(datetime, Payment_Date, 120), 'yyyy-MM') = FORMAT(GETDATE(), 'yyyy-MM')
GROUP BY Income_Expense_Name
ORDER BY Amount DESC


        '''
        cursor.execute(query)
        summary_data = cursor.fetchall()

        formatted_data = {
            'income': [row[0] for row in summary_data],
            'net_amounts': [row[1] for row in summary_data]
        }

        return formatted_data


    except Exception as e:
        print(f"Error fetching income and expense summary: {str(e)}")
        return [], []

    finally:
        cursor.close()


def fetch_expenses(connection):
    cursor = connection.cursor()
    try:
        cursor.execute("""
                   SELECT TOP 5
    Income_Expense_Name,
    SUM(CAST(Amount AS FLOAT)) AS Amount
FROM IncomeExpenseTable
WHERE Type = 'Expense'
    AND FORMAT(CONVERT(datetime, Payment_Date, 120), 'yyyy-MM') = FORMAT(GETDATE(), 'yyyy-MM')
GROUP BY Income_Expense_Name
ORDER BY Amount DESC;

                """, )

        summary_data = cursor.fetchall()
        formatted_data = {
            'expense': [row[0] for row in summary_data],
            'net_amounts': [row[1] for row in summary_data]
        }

        return formatted_data

    except Exception as e:
        print(f"Error fetching incomes data: {str(e)}")
        return []

    finally:
        cursor.close()


@app.route('/')
def accounts():
    connection = check_database_connection()

    try:
        if not connection:
            connection = check_database_connection()

        if connection:
            financial_data = fetch_monthly_financial_data(connection)
            accounts = fetch_accounts_data(connection)
            account_summary = fetch_account_summary(connection)
            income_data = fetch_income_list(connection)
            expense_data = fetch_expenses(connection)

            # Debugging print statements
            print("Financial Data:", financial_data)
            print("Accounts:", accounts)
            print("Account Summary:", account_summary)
            print("Income Data:", income_data)
            print("Expense Data:", expense_data)

            colors = ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#858796']

            # Handle empty income or expense data gracefully
            income_list = income_data.get('income', [])
            expense_list = expense_data.get('expense', [])

            # Ensure the colors don't exceed the income/expense list lengths
            labeled_colors = list(zip(income_list, colors[:len(income_list)])) if income_list else []
            labeled_expenses_colors = list(zip(expense_list, colors[:len(expense_list)])) if expense_list else []

            print("Labeled Colors:", labeled_colors)
            print("Labeled Expenses Colors:", labeled_expenses_colors)

            return render_template('accounts.html',
                                   labeled_colors=labeled_colors,
                                   colors=colors,
                                   accounts=accounts,
                                   account_summary=account_summary,
                                   financial_data=financial_data,
                                   income_data=income_data,
                                   expense_data=expense_data,
                                   labeled_expenses_colors=labeled_expenses_colors)
        else:
            return render_template('error.html', message="Could not connect to the database. Please try again later.")

    except Exception as e:
        print(f"Error in account_balances route: {str(e)}")
        return render_template('error.html', message="An unexpected error occurred. Please try again later.")

    finally:
        if connection:
            connection.close()


@app.route('/addTransaction')
def addTransaction():
    return render_template('addTransaction.html')


@app.route('/accounts/<account_name>')
def accountData(account_name):
    print(f"Account Name: {account_name}")  # Debug line

    connection = check_database_connection()
    if connection is None:
        return "Database connection error", 500  # Return an error message or page if connection fails

    print("CONNECTED TO DATABASE")
    person= account_name.title()
    try:
        with connection.cursor(as_dict=True) as cursor:
            query = "SELECT * FROM IncomeExpenseTable WHERE Income_Expense_Name LIKE %s ORDER BY Payment_Date DESC"
            cursor.execute(query, ('%' + account_name + '%',))
            transactions = cursor.fetchall()
    except pymssql.Error as e:
        print(f"Error fetching data from the database: {str(e)}")
        transactions = []  # Ensure transactions is defined
    finally:
        connection.close()

    # Simple template rendering to verify if template works without data
    return render_template("finance_report.html", transactions=transactions, account=False,person_name=person)


@app.route('/expense_data')
def expense_data():
    connection = check_database_connection()

    try:
        if connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT e.expense_id, e.expense_title, s.subtype_title
                FROM ExpenseTypes e
                LEFT JOIN ExpenseSubtypes s ON e.expense_id = s.expense_id
            """)
            rows = cursor.fetchall()

            expense_data = {}
            for expense_id, expense_title, subtype_title in rows:
                if expense_id not in expense_data:
                    expense_data[expense_id] = {
                        "expense_title": expense_title,
                        "subtypes": []
                    }
                if subtype_title:
                    expense_data[expense_id]["subtypes"].append(subtype_title)

            # Convert the dictionary to the format needed
            response_data = {
                'types': [{'expense_id': k, 'expense_title': v['expense_title']} for k, v in expense_data.items()],
                'subtypes': {str(k): v['subtypes'] for k, v in expense_data.items()}
            }

            return jsonify(response_data)
        else:
            return "Error: No database connection"

    except Exception as e:
        print(f"Error in expense_data route: {str(e)}")
        return "Error in expense_data route"

    finally:
        if connection:
            connection.close()


@app.route('/income_data')
def income_data():
    connection = check_database_connection()

    try:
        if connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT e.income_id, e.income_title, s.subtype_title
                FROM incomeTypes e
                LEFT JOIN incomeSubtypes s ON e.income_id = s.income_id
            """)
            rows = cursor.fetchall()

            income_types = {}
            income_subtypes = []

            for income_id, income_title, subtype_title in rows:
                if income_title not in income_types:
                    income_types[income_title] = income_id
                if subtype_title:
                    income_subtypes.append({
                        'subtype_title': subtype_title,
                        'income_id': income_id
                    })

            # Convert the dictionary to the format needed
            response_data = {
                'types': [{'income_id': v, 'income_title': k} for k, v in income_types.items()],
                'subtypes': income_subtypes
            }

            return jsonify(response_data)
        else:
            return "Error: No database connection"

    except Exception as e:
        print(f"Error in income_data route: {str(e)}")
        return "Error in income_data route"

    finally:
        if connection:
            connection.close()


@app.route('/add_income', methods=['POST'])
def add_income():
    connection = check_database_connection()

    if connection:
        try:
            cursor = connection.cursor()

            amount = float(request.form['amount'])
            income_title = request.form['income_type']
            payment_to = request.form['income_subtype']
            description = request.form.get('description', '')
            submission_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            income_expense_name = f"{income_title} - {payment_to}"

            # Get current bank balance from last record
            cursor.execute("""
                            SELECT accounts_balance
                            FROM accounts
                            WHERE accounts_name = 'Bank'
                        """)
            last_bank_balance = cursor.fetchone()
            current_bank_balance = last_bank_balance[0] if last_bank_balance else 0.00

            new_bank_balance = current_bank_balance + amount

            # Optional: get current account balance (if needed for 'Account_Balance')
            cursor.execute("""
                SELECT accounts_balance
                FROM accounts
                WHERE accounts_name = %s
            """, (payment_to,))
            account_balance_result = cursor.fetchone()
            current_account_balance = account_balance_result[0] if account_balance_result else 0.00
            new_account_balance = current_account_balance + amount

            # Insert with Bank_Balance and Account_Balance
            cursor.execute("""
                INSERT INTO IncomeExpenseTable
                    (Income_Expense_Name, Description, Amount, Type, Payment_Date, Bank_Balance, Account_Balance)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                income_expense_name,
                description,
                amount,
                'Income',
                submission_datetime,
                new_bank_balance,
                new_account_balance
            ))

            # Update individual account balance if it's an investment
            if income_title == 'Investments':
                cursor.execute("""
                    UPDATE accounts
                    SET accounts_balance = accounts_balance + %s
                    WHERE accounts_name = %s
                """, (amount, payment_to))

            # Always update Bank account balance
            cursor.execute("""
                UPDATE accounts
                SET accounts_balance = accounts_balance + %s
                WHERE accounts_name = 'Bank'
            """, (amount,))

            connection.commit()
            return jsonify({'status': 'success', 'message': 'Income successfully added!'})

        except Exception as e:
            connection.rollback()
            print(f"Error in add_income route: {str(e)}")
            return jsonify({'status': 'error', 'message': 'Error in adding income'})

        finally:
            connection.close()
    else:
        return jsonify({'status': 'error', 'message': 'Error: No database connection'})




@app.route('/add_expense', methods=['POST'])
def add_expense():
    connection = check_database_connection()

    if connection:
        try:
            cursor = connection.cursor()

            amount = float(request.form['amount'])  # Convert to float for numeric operations
            expense_title = request.form['expense_type']
            payment_to = request.form['expense_subtype']
            description = request.form.get('description', '')
            submission_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            income_expense_name = f"{expense_title} - {payment_to}"

            # Get current Bank balance from accounts table
            cursor.execute("""
                SELECT accounts_balance
                FROM accounts
                WHERE accounts_name = 'Bank'
            """)
            bank_balance_result = cursor.fetchone()
            current_bank_balance = bank_balance_result[0] if bank_balance_result else 0.00
            new_bank_balance = current_bank_balance - amount

            # Determine if we should subtract from the individual account
            update_account_balance = expense_title in ['Profit Withdrawal', 'Employee Salary', 'Employee Loan']

            if update_account_balance:
                # Get current account balance
                cursor.execute("""
                    SELECT accounts_balance
                    FROM accounts
                    WHERE accounts_name = %s
                """, (payment_to,))
                account_balance_result = cursor.fetchone()
                current_account_balance = account_balance_result[0] if account_balance_result else 0.00
                new_account_balance = current_account_balance + amount

                # Update the account balance
                cursor.execute("""
                    UPDATE accounts
                    SET accounts_balance = accounts_balance + %s
                    WHERE accounts_name = %s
                """, (amount, payment_to))
            else:
                new_account_balance = None  # not updated/tracked for this expense type

            # Always update Bank account balance
            cursor.execute("""
                UPDATE accounts
                SET accounts_balance = accounts_balance - %s
                WHERE accounts_name = 'Bank'
            """, (amount,))

            # Insert into IncomeExpenseTable with balance fields
            cursor.execute("""
                INSERT INTO IncomeExpenseTable 
                    (Income_Expense_Name, Description, Amount, Type, Payment_Date, Bank_Balance, Account_Balance)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                income_expense_name,
                description,
                amount,
                'Expense',
                submission_datetime,
                new_bank_balance,
                new_account_balance
            ))

            connection.commit()
            return jsonify({'status': 'success', 'message': 'Expense successfully added!'})

        except Exception as e:
            connection.rollback()
            print(f"Error in add_expense route: {str(e)}")
            return jsonify({'status': 'error', 'message': 'Error in adding expense'})

        finally:
            connection.close()
    else:
        return jsonify({'status': 'error', 'message': 'Error: No database connection'})




@app.route('/get_payables')
def get_payables():
    connection = check_database_connection()

    if connection:
        try:
            cursor = connection.cursor()

            # Fetching data from payables table
            cursor.execute("""SELECT vendor, amount, pendingsince FROM payables""")
            rows = cursor.fetchall()  # Correctly fetch the rows from the cursor

            payables_list = []
            total_payables = 0  # Initialize total payables

            for payable in rows:
                vendor, amount, pending_since = payable
                pending_days = (datetime.now().date() - pending_since).days

                # Calculate total payables
                total_payables += amount

                # Prepare payables data to return
                payables_list.append({
                    'vendor': vendor,
                    'amount': f"Rs {amount}",
                    'pending_since': pending_since.strftime('%d %b %Y'),
                    'pending_days': pending_days
                })
            print(total_payables)

            # Return both the payables list and the total payables
            return jsonify({
                'payables': payables_list,
                'total_payables': f"Rs {total_payables}"
            })

        except Exception as e:
            connection.rollback()
            print(f"Error in get_payables route: {str(e)}")
            return jsonify({'status': 'error', 'message': 'Error in fetching payables'})

        finally:
            connection.close()
    else:
        return jsonify({'status': 'error', 'message': 'Error: No database connection'})



@app.route('/mark_paid', methods=['POST'])
def mark_paid():
    vendor = request.args.get('vendor')

    if not vendor:
        return jsonify({'status': 'error', 'message': 'Vendor parameter is missing'})
    print(vendor)
    connection = check_database_connection()
    if connection:
        try:
            cursor = connection.cursor()

            # Use named parameters for SQL Server
            cursor.execute("DELETE FROM payables WHERE vendor = %s", (vendor))

            connection.commit()
            return jsonify({'status': 'success', 'message': 'Payable marked as paid'})

        except Exception as e:
            connection.rollback()
            print(f"Error in mark_paid route: {str(e)}")
            return jsonify({'status': 'error', 'message': 'Error in marking payable as paid'})

        finally:
            connection.close()
    else:
        return jsonify({'status': 'error', 'message': 'Error: No database connection'})


@app.route('/update_amount', methods=['POST'])
def update_amount():
    try:
        data = request.get_json()
        vendor = data.get('vendor')
        new_amount = data.get('amount')
        print(f"{vendor} : {new_amount}")

        if not vendor or not new_amount:
            return jsonify({'status': 'error', 'message': 'Vendor or amount is missing'})

        connection = check_database_connection()
        if connection:
            try:
                cursor = connection.cursor()

                # Use parameterized queries to prevent SQL injection
                cursor.execute("UPDATE payables SET amount = %s WHERE vendor = %s", (new_amount, vendor))

                connection.commit()
                return jsonify({'status': 'success', 'message': 'Amount updated successfully'})

            except Exception as e:
                connection.rollback()
                print(f"Error in update_amount route: {str(e)}")
                return jsonify({'status': 'error', 'message': 'Error updating amount'})

            finally:
                connection.close()
        else:
            return jsonify({'status': 'error', 'message': 'Error: No database connection'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error: {str(e)}'})


@app.route('/add_payable', methods=['POST'])
def add_payable():
    try:
        data = request.get_json()
        vendor = data.get('vendor')
        amount = data.get('amount')
        pending_since = data.get('pending_since')

        if not vendor or not amount or not pending_since:
            return jsonify({'status': 'error', 'message': 'All fields are required'})

        connection = check_database_connection()
        if connection:
            try:
                cursor = connection.cursor()

                # Insert new payable into the database
                cursor.execute("""
                    INSERT INTO payables (vendor, amount, pendingsince)
                    VALUES (%s, %s, %s)
                """, (vendor, amount, pending_since))

                connection.commit()
                return jsonify({'status': 'success', 'message': 'Payable added successfully'})

            except Exception as e:
                connection.rollback()
                print(f"Error in add_payable route: {str(e)}")
                return jsonify({'status': 'error', 'message': 'Error adding payable'})

            finally:
                connection.close()
        else:
            return jsonify({'status': 'error', 'message': 'Error: No database connection'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error: {str(e)}'})


if __name__ == "__main__":
    app.run(port=5001)
