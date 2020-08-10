A program to migrate course from StreamitUP (2016 and further) to HUJI Panopto.


## Instrctions for setting up Panopto API
1. Sign in to the Panopto web site as Administarator
2. Click the System icon at the left-bottom corner.
3. Click API Clients
4. Click New
5. Enter arbitrary Client Name
6. Select Server-side Web Application type.
7. Enter https://localhost into CORS Origin URL.
8. Enter http://localhost:9127/redirect into Redirect URL.
9. The rest can be blank. Click "Create API Client" button.
10. Note the created Client ID and Client Secret.

## Usage
pip install requirements.txt
upload.py --client-id <panopto client id> --client-secret <panopto client secret> --course-id <HUJI course id> --semester <semester> --year <year> --folder-id <panotpo folder id>
  
Please note:
Semester: "Semster 1" or "Semester 2" or "Summer"
Year: The starting of the school year. i.e 2017-2018 is 2017.
folder-id: Optional argument for specific panopto id. If ignored, will search for the course in the Moodle structure.
