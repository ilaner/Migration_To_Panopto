import re
import pytz

PANOPTO_SERVER_NAME = 'huji.cloud.panopto.eu'
PANOPTO_CLIEND_ID = None
PANOPTO_SECRET = None

YEARS = {2018: '2018-19',
         2019: '2019-20',
         2020: '2020-21'}


REGEX = re.compile(r'[\n\r\t]')
ISRAEL = pytz.timezone('Israel')

xml = """<?xml version="1.0" encoding="utf-8"?>
<Session xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns="http://tempuri.org/UniversalCaptureSpecification/v1">
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
</Session>"""
