from agent import run_agent_loop

# entry point
def main():
    main_instructions = """You are in Row 51 of the FX Reimbursements 24-25 Google Sheet. You have access to a Payments tab in the browser.
        Only record values from a box that you have selected. Do not look at any other rows. Do not use Alt Tab.
        Check every step before proceeding. If a step fails, try to fix it and do not move on.
        Execute the following steps in the browser. """
    
    fillout_instructions = main_instructions + """
        SETTING UP THE PAYMENT REQUEST:
        1. Locate the @stanford.edu email under Email Address. The username that comes before the @ is the SUNet ID. It should contain mostly letters.
        2. Find the "Project Name" column. Remember this as the project name
        3. Click on the Payments Tab.
        4. Click the "New Payment Request Button"
        5. Click on "Student Reimbursement"
        6. Fill in the Payee SUNet ID field with the SUNet ID you found in step 5.
        7. Fill in the Summary Description with the Project Name (Column E) and Description of purchase (Column F).
        8. Click the "Next" button in the top right"""

    fillout_instructions_2 = main_instructions + """
        FILLING OUT THE PAYMENT REQUEST:
        1. Switch back to the FX Reimbursements 24-25 Tab.
        2. Move several columns to the right using the right arrow key, until you are in the Amount column. Make note of the Description of purchase, Vendor name, Total amount and Date of purchase.
        3. Navigate back to the Payment Details tab.
        4. Double click on the date box, below the Document Date header.
        5. First click the year field (2025), then select the correct year from the dropdown.
        6. Then click the month field (February), then select the correct month from the dropdown.
        7. Then select the correct day from the calendar.
        8. Click on the text box under "Document Type".
        9. Type the letter "R" in the text box.
        10. Click on the text box in the "Vendor" column. Type in the Vendor name.
        11. Click on the text box in the "Amount" column and type in the Amount.
        12. Double click on the text box in the "Account" field.
        13. Click on "The Stanford Fund Partnership".
        14. Click "Save" in the top right corner."""


    document_instructions = """
        You are in Row 51 of the FX Reimbursements 24-25 Google Sheet.
        Only record values from a box that you have selected. Do not look at any other rows. Do not use Alt Tab.
        Check every step before proceeding. If a step fails, try to fix it and do not move on.
        Execute the following steps in the browser:

        DOWNLOADING THE DOCUMENTS:
        1. Switch back to the FX Reimbursements 24-25 Google Sheet tab
        2. Go one column to the right, so that you are in the column labeled "Itemized receipt upload". Click on the link. This will open a pop-up.
        3. Click on the image in the pop-up. This will open a new tab.
        4. Wait for the document to load.
        5. Click the download icon.
        6. Wait for the document to download. Remember the document name.
        7. Switch back to the FX Reimbursements 24-25 Tab.
        8. Use the right arrow key to move to Column H. This is the column labeled "Credit card or bank statement". Click on the link. This will open a pop-up.
        9. Click on the image in the pop-up. This will open a new tab.
        10. Wait for the document to load.
        11. Click the download icon.
        12. Wait for the document to download. Remember the document name.

        UPLOADING DOCUMENTS:
        13. Click the Paperclip icon.
        14. Click inside the large white blank rectangle.
        15. A file explorer will pop up. Look in the file explorer for the first document you downloaded.
        16. Click on the document and make sure it is highlighted blue.
        17. Press the blue "Open" button in the bottom right corner.
        18. Click the white rectangle again.
        19. Look in the file explorer for the second document you downloaded.
        20. Click on the document and make sure it is highlighted blue.
        21. Click the blue "Open" button in the bottom right corner.
        22. Wait for the documents to upload.
        23. Click the "OK" button in the bottom right corner.
        24. Click "Save" in the top right corner.
        """
    # instructions = (
    #     """
    #     Ask the user any clarifying questions when needed. Check every step before proceeding.

    #     Execute the following steps in the browser:
    #     1. Click on the Payments Tab.
    #     2. Click the "New Payment Request Button"
    #     3. Click on "Student Reimbursement"
    #     4. Switch back to the FX Reimbursements 24-25 Tab
    #     5. Locate the @stanford.edu email in the form response. The username that comes before the @ is the SUNet ID. It should contain mostly letters.
    #     6. Find the answer to "What FX project or team is this for?" and remember this as the project name
    #     7. Scroll down a full screen using the space key. Click on the document uploaded under "Itemized receipt upload". This will open a new tab.
    #     8. Download the document. This will open a new tab.
    #     9. Switch back to the FX Reimbursements 24-25 Tab.
    #     9. Click on the document uploaded under "Credit card or bank receipt upload". This will open a new tab.
    #     10. Download the document. This will open a new tab.
    #     11. Switch back to the FX Reimbursements 24-25 Tab.
    #     12. Make note of the Vendor name and Description of purchase. 
    #     13. Scroll down a full screen using the space key. Make note of the Total amount and Date of purchase. If you cannot see the total amount, scroll down more.
    #     14. Navigate back to the Payment Details tab.
    #     15. Fill in the Payee SUNet ID field with the SUNet ID you found in step 5.
    #     16. Fill in the Summary Description with the Project Name and Description of purchase.
    #     17. Double click on Document Date.
    #     18. Navigate to the correct calendar date.
    #     19. Click on Document Type.
    #     20. Select "Receipt" as the Document Type.
    #     21. Click the Paperclip icon.
    #     22. Upload the 2 downloaded documents.
    #     23. Click "OK" 
    #     24. Click on and fill in the Vendor name field.
    #     25. Click on and fill in the Amount field.
    #     26. Click "Save" in the top right corner.
    #     """
    # )
    run_agent_loop(fillout_instructions)
    run_agent_loop(fillout_instructions_2)
    run_agent_loop(document_instructions)

if __name__ == "__main__":
    main()