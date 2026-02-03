set-dues.py 

Functions 

    set_dues_starters, takes in input amount 
        Checks for admin role, if the user doesn't have admin ends interaction. 
        Then select rows named dues/$ and changes column named starter in the database to the new amount. If the rows don't exist then it create them with default value then edits the column starter to the input value 


    set_dues_substitutes takes in input amount
        Checks for admin role, if the user doesn't have admin ends interaction. 
        Then select rows named dues/$ and changes column named substitues in the database to the new amount. If the rows don't exist then it create them with default value then edits the column substitues to the input value

    set_dues_non_players takes in input amount 
        Checks for admin role, if the user doesn't have admin ends interaction. 
        Then select rows named dues/$ and changes column named substitues in the database to the new amount. If the rows don't exist then it create them with default value then edits the column substitues to the input value


generate.py

Function 

    generate_dues
        Checks for admin role, if the user doesn't have admin ends interaction
        Then checks if dues has been set and if there is an active team.
        If both are set then create a workbook with sheets for active team games which record the active team's detail and fees in a preset format style
    