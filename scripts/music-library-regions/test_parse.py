"""The readers of the regional sources, on small pieces of each page written here (no network, no
saved page committed). ``python3 scripts/music-library-regions/test_parse.py``"""

from __future__ import annotations

import unittest
from datetime import date

import parse

SPANISHCHARTS = (
    "<tr onclick=\"location.href='showitem.asp?interpret=Band+Aid+20&titel=Do+They+Know+It%27s+Christmas%3F&cat=s';\">"
    '<td class="text"><b>1</b></td><td class="text"><b>1</td></td><td></td><td></td>'
    '<td class="text"><a href="showitem.asp?x" class="navb"><b>Band Aid 20</b><br>Do They Know It\'s Christmas?</a></td></tr>'
    "<tr onclick=\"location.href='showitem.asp?interpret=Depeche+Mode&titel=Enjoy+The+Silence+04&cat=s';\">"
    '<td class="text"><b>10</b></td><td class="text"><b><img src="/images/new.gif" border=0></td></td><td></td><td></td>'
    '<td class="text"><a href="showitem.asp?x" class="navb"><b>Depeche Mode</b><br>Enjoy The Silence 04</a></td></tr>'
    "<tr onclick=\"location.href='showitem.asp?interpret=J+Balvin+%26+Bad+Bunny&titel=Qu%E9+pretendes&cat=s';\">"
    '<td class="text"><b>100</b></td><td class="text"><b>RE</td></td><td></td><td></td>'
    '<td class="text"><a href="showitem.asp?x" class="navb"><b>J Balvin &amp; Bad Bunny</b><br>Qu\xe9 pretendes</a></td></tr>'
).encode("latin-1")

LOS40_WEEK = (
    '<main><ul class="lst-can">'
    '<li id="4c752801b0cfb4bfeaf7857c67ffeddc" class="mos" data-youtube-url="http://www.youtube.com/watch?v=XXywgkY2O5U&amp;ob=av2e">'
    '<div class="pos"><p>1</p></div><div><h2>Boys will be boys</h2><span>Paulina Rubio</span></div>'
    '<a href="https://music.apple.com/es/album/x/1444398602?i=1444398607&amp;uo=4">Apple</a></li>'
    '<li id="bb9192918be3c923218c39610a007a0a" data-youtube-url="http://www.youtube.com/watch?v=_KSyWS8UgA4">'
    '<div class="pos"><p>2</p></div><div><h2>Yo te esperaré</h2><span>Cali y El Dandee</span></div></li>'
    "</ul></main>"
).encode()

LOS40_YEAR = (
    '<ul class="lst-num-1"><li class="mos" data-youtube-url=""><div class="dat"><div>'
    "<h2>¿Cómo pudiste hacerme esto a mí?</h2><span>Alaska y Dinarama</span><b> Semana del 5 de enero</b></div>"
    '<a href="/lista40/listas-anteriores/1985-01-05">Ver lista completa</a></div></li>'
    '<li class="mos" data-youtube-url="https://www.youtube.com/watch?v=07HFjbnbTaU"><div class="dat"><div>'
    "<h2>Monday, monday</h2><span>The Mamas &amp;amp; The Papas</span></div>"
    '<a href="/lista40/listas-anteriores/1985-01-12">Ver lista completa</a></div></li></ul>'
).encode()

KWORB = (
    "<table><tbody><tr>"
    '<td class="text mp"><div><a href="../artist/0tmw.html">Manuel Turizo</a> - '
    '<a href="../track/3tt9i3Hhzq84dPS8H7iSiJ.html">La Bachata</a></div></td>'
    '<td>229</td><td>36</td><td>1</td><td class="np mini text">(x2)</td><td>4,853,775</td><td>362,146,007</td></tr>'
    "</tbody></table>"
).encode()

WIKI_EN = """{|  class="wikitable"
! Issue date !! Song !! Artist
|-
| 6 January  || rowspan=2 | "[[Todo El Tiempo Del Mundo]]" || rowspan=2 | [[Manolo Otero]]
|-
| 13 January
|-
| 20 January || "[[Believe (Cher song)|Believe]]" || [[Cher]]
|}"""

WIKI_ES = """{| class="sortable wikitable"
|-
! Fecha || Posición || Artista || Sencillo || País
|-
 || 1 || 02/01/1982 || [[Ricchi e Poveri]] || ''[[Será porque te amo]] || {{ITA}}
|-
 || 02/01/1982 || 2 || [[Miguel Bosé]] ||'' Márchate ya || {{ESP}}
|}"""

WIKI_CA = """{| class="wikitable sortable"
!#
!Cançó
!Reproduccions{{efn|nota}}
!Artista/Grup
!Àlbum
!Any de publicació
|-
!1
|[[Milionària]]
| align=center |86.523.138
|[[Rosalía]]
| align=center |''<small>(Senzill)</small>''
| align=center |2019
|}"""


def apecat_xml(fragmented: bool) -> str:
    """A page of ``pdftohtml -xml``: the header, then two rows; the old PDFs cut words in pieces."""
    fonts = (
        '<fontspec id="0" size="35" family="Montserrat-ExtraBold" color="#322e2d"/>'
        '<fontspec id="1" size="15" family="Montserrat" color="#898787"/>'
        '<fontspec id="3" size="16" family="Montserrat-Medium" color="#322e2d"/>'
    )
    header = (
        '<text top="69" left="300" width="200" height="20" font="0">CANÇONS EN CATALÀ</text>'
        '<text top="138" left="300" width="90" height="20" font="1">SETEMBRE</text>'
        '<text top="141" left="400" width="200" height="20" font="1">14.08.2026 - 10.09.2026</text>'
    )
    if fragmented:
        title = ('<text top="196" left="353" width="5" height="20" font="0">I</text>'
                 '<text top="198" left="359" width="15" height="20" font="0">n</text>'
                 '<text top="196" left="380" width="8" height="20" font="0">N</text>'
                 '<text top="198" left="388" width="20" height="20" font="0">ight</text>')
    else:
        title = '<text top="201" left="352" width="132" height="20" font="0">El Ventilador</text>'
    rows = (
        '<text top="206" left="125" width="20" height="46" font="0">1</text>'
        + title
        + '<text top="225" left="352" width="233" height="20" font="3">Banda Neon, Buhos</text>'
        '<text top="396" left="129" width="10" height="15" font="1">2</text>'
        '<text top="398" left="213" width="8" height="13" font="1">2</text>'
        '<text top="380" left="316" width="184" height="19" font="0">Diumenge Sense Drama</text>'
        '<text top="402" left="316" width="85" height="18" font="3">Els Catarres</text>'
        '<text top="395" left="669" width="92" height="16" font="1">Halley Records</text>'
    )
    return f'<pdf2xml>{fonts}<page number="1">{header}{rows}</page></pdf2xml>'


class Readers(unittest.TestCase):
    def test_spanishcharts(self) -> None:
        rows = parse.spanishcharts_week(SPANISHCHARTS)
        self.assertEqual([r.rank for r in rows], [1, 10, 100])  # a new entry shows an image
        self.assertEqual(rows[0].key, "Band Aid 20|Do They Know It's Christmas?")
        self.assertEqual((rows[2].artist, rows[2].title), ("J Balvin & Bad Bunny", "Qué pretendes"))

    def test_los40(self) -> None:
        rows = parse.los40_week(LOS40_WEEK)
        self.assertEqual([(r.rank, r.title, r.artist) for r in rows],
                         [(1, "Boys will be boys", "Paulina Rubio"), (2, "Yo te esperaré", "Cali y El Dandee")])
        self.assertEqual((rows[0].youtube_id, rows[0].apple_id), ("XXywgkY2O5U", "1444398607"))
        ones = parse.los40_number_ones(LOS40_YEAR)
        self.assertEqual([d for d, _ in ones], [date(1985, 1, 5), date(1985, 1, 12)])
        self.assertEqual(ones[1][1].artist, "The Mamas & The Papas")  # escaped twice on the page
        self.assertEqual(ones[1][1].youtube_id, "07HFjbnbTaU")

    def test_kworb(self) -> None:
        [row] = parse.kworb_totals(KWORB)
        self.assertEqual((row.artist, row.title, row.spotify_id), ("Manuel Turizo", "La Bachata", "3tt9i3Hhzq84dPS8H7iSiJ"))
        self.assertEqual(row.extra, {"weeks": 229, "top10_weeks": 36, "peak": 1, "peak_times": 2,
                                     "peak_streams": 4853775, "streams": 362146007})

    def test_wikipedia(self) -> None:
        ones = parse.wikipedia_number_ones(WIKI_EN, 1975)
        self.assertEqual([(d.isoformat(), r.title, r.artist) for d, r in ones], [
            ("1975-01-06", "Todo El Tiempo Del Mundo", "Manolo Otero"),
            ("1975-01-13", "Todo El Tiempo Del Mundo", "Manolo Otero"),  # the rowspan filled down
            ("1975-01-20", "Believe", "Cher"),
        ])
        top = parse.wikipedia_top10(WIKI_ES)  # 1982 has the place and the date the other way round
        self.assertEqual([(d.isoformat(), r.rank, r.title) for d, r in top],
                         [("1982-01-02", 1, "Será porque te amo"), ("1982-01-02", 2, "Márchate ya")])
        [song] = parse.viquipedia_spotify(WIKI_CA)
        self.assertEqual((song.title, song.artist, song.extra), ("Milionària", "Rosalía", {"streams": 86523138, "year": 2019}))

    def test_apecat(self) -> None:
        listed = parse.apecat_list(apecat_xml(False), "BMAT-APECAT-Top30-setembre-LlenguaCatalana.pdf")
        self.assertEqual((listed.series, listed.start, listed.end, listed.yearly),
                         ("llengua", date(2026, 8, 14), date(2026, 9, 10), False))
        self.assertEqual([(r.rank, r.title, r.artist) for r in listed.rows],
                         [(1, "El Ventilador", "Banda Neon, Buhos"), (2, "Diumenge Sense Drama", "Els Catarres")])
        old = parse.apecat_list(apecat_xml(True), "APECAT-Top30-Setembre-CatProd.pdf")
        self.assertEqual(old.series, "produccio")  # the file name says the series
        self.assertEqual(old.rows[0].title, "In Night")  # pieces of one line joined, spaces kept

    def test_compared(self) -> None:
        self.assertEqual(parse.compared("Sebastián Yatra · L·L"), "sebastian yatra ll")


if __name__ == "__main__":
    unittest.main()
