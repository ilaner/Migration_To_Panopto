import re
import pytz

PANOPTO_SERVER_NAME = 'huji.cloud.panopto.eu'
PANOPTO_CLIEND_ID = None
PANOPTO_SECRET = None


COURSE_ID = None
SEMESTER = None
YEAR = None
FOLDER_ID = None

YEARS = {2018: '2018-19',
         2019: '2019-20',
         2020: '2020-21'}


REGEX = re.compile(r'[\n\r\t]')
ISRAEL = pytz.timezone('Israel')

xml = """
<Session>
  <Title>Test session with audio, video and a presentation</Title>
  <Description/>
  <Date>2018-01-15T00:00:00.000-00:00</Date>
  <Videos>
    <Video>
      <Start>PT0S</Start>
      <File>primary.mp4</File>
      <Cuts/>
      <TableOfContents>
      </TableOfContents>
      <Type>Audio</Type>
      <Transcripts/>
    </Video>
    <Video>
      <Start>PT0S</Start>
      <File>secondary.mp4</File>
      <Cuts/>
      <TableOfContents/>
      <Type>Secondary</Type>
      <Transcripts/>
    </Video>
  </Videos>
  <Presentations>
  </Presentations>
  <Images/>
  <Cuts>
  </Cuts>
  <Tags/>
  <Extensions/>
  <Attachments/>
</Session>
"""