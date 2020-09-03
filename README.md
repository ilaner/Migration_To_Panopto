
A program to migrate course from StreamitUP (2016 and further) to HUJI Panopto.

<!-- ABOUT THE PROJECT -->
## About The Project

The program purpose is migrating Hebrew University Jerusalem recording lectures database from StreamitUp to Panopto.

In 2020, during COVID-19 pandemic, the Hebrew University changed its recording company from StreamitUp to Panopto, and they had to move their archive as well.

This project was built only with access to StreamitUP website, and without any access to their API. The videos and the metadata were parsed manually, and created the database of all the videos that was recorded using this service.

 After collecting the database, upload to panopto was needed. It was used with panopto upload API using UCS method, which I used the example here: 

 [panopto upload example](https://github.com/Panopto/upload-python-sample)

 It was neccessery in order to upload both cam and screen recordings into one session.

 The metadata collected was used to upload the lectures into the correct path, with the correct name and date.

 A lot of effort was made for this project, and I hope the outcome is good enough. 

<!-- GETTING STARTED -->
## Getting Started

This is an example of how you may give instructions on setting up your project locally.
To get a local copy up and running follow these simple example steps.

### Prerequisites

Use Python 3.8, and run
```sh
pip install -r requirements.txt

```

### Installation

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



<!-- USAGE EXAMPLES -->
## Usage
The client id and client secret are necessary. If you provide only them, all the database will be migrated.
You can add course id, year, semseter. In this case only what you entered will be migrated.
In addition, you can add folder id. In this case, what you ask to upload will be uploaded to this specific panopto folder id.

In order to run, run with shell, or with Pycharm with those arguments:
```
upload.py --client-id <panopto client id> --client-secret <panopto client secret> --course-id <HUJI course id> --semester <semester> --year <year> --folder-id <panotpo folder id>
```

Please note:
- Semester: "Semster 1" or "Semester 2" or "Summer"
- Year: The starting of the school year. i.e 2017-2018 is 2017.
- folder-id: Optional argument for specific panopto id. If ignored, will search for the course in the Moodle structure.



<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.



<!-- CONTACT -->
## Contact

Your Name - ilanerukh@gmail.com








