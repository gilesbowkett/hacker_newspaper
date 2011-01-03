# http://hacketal.com/#hnrss
from xml.sax.saxutils import escape

import urllib
import re
import os
import urlparse
import HTMLParser
import feedparser
from BeautifulSoup import BeautifulSoup
from pprint import pprint

import codecs
import sys
streamWriter = codecs.lookup('utf-8')[-1]
sys.stdout = streamWriter(sys.stdout)


HN_RSS_FEED = "http://news.ycombinator.com/rss"

NEGATIVE    = re.compile("comment|meta|footer|footnote|foot")
POSITIVE    = re.compile("post|hentry|entry|content|text|body|article")
PUNCTUATION = re.compile("""[!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~]""")


def grabContent(link, html):
    
    replaceBrs = re.compile("<br */? *>[ \r\n]*<br */? *>")
    html = re.sub(replaceBrs, "</p><p>", html)
    
    try:
        soup = BeautifulSoup(html)
    except HTMLParser.HTMLParseError:
        return ""
    
    # REMOVE SCRIPTS
    for s in soup.findAll("script"):
        s.extract()
    
    allParagraphs = soup.findAll("p")
    topParent     = None
    
    parents = []
    for paragraph in allParagraphs:
        
        parent = paragraph.parent
        
        if (parent not in parents):
            parents.append(parent)
            parent.score = 0
            
            if (parent.has_key("class")):
                if (NEGATIVE.match(parent["class"])):
                    parent.score -= 50
                if (POSITIVE.match(parent["class"])):
                    parent.score += 25
                    
            if (parent.has_key("id")):
                if (NEGATIVE.match(parent["id"])):
                    parent.score -= 50
                if (POSITIVE.match(parent["id"])):
                    parent.score += 25

        if (parent.score == None):
            parent.score = 0
        
        innerText = paragraph.renderContents() #"".join(paragraph.findAll(text=True))
        if (len(innerText) > 10):
            parent.score += 1
            
        parent.score += innerText.count(",")
        
    for parent in parents:
        if ((not topParent) or (parent.score > topParent.score)):
            topParent = parent

    if (not topParent):
        return ""
            
    # REMOVE LINK'D STYLES
    styleLinks = soup.findAll("link", attrs={"type" : "text/css"})
    for s in styleLinks:
        s.extract()

    # REMOVE ON PAGE STYLES
    for s in soup.findAll("style"):
        s.extract()

    # CLEAN STYLES FROM ELEMENTS IN TOP PARENT
    for ele in topParent.findAll(True):
        del(ele['style'])
        del(ele['class'])
        
    killDivs(topParent)
    clean(topParent, "form")
    clean(topParent, "object")
    clean(topParent, "iframe")
    
    fixLinks(topParent, link)
    
    return topParent.renderContents()
    

def fixLinks(parent, link):
    tags = parent.findAll(True)
    
    for t in tags:
        if (t.has_key("href")):
            t["href"] = urlparse.urljoin(link, t["href"])
        if (t.has_key("src")):
            t["src"] = urlparse.urljoin(link, t["src"])


def clean(top, tag, minWords=10000):
    tags = top.findAll(tag)

    for t in tags:
        if (t.renderContents().count(" ") < minWords):
            t.extract()


def killDivs(parent):
    
    divs = parent.findAll("div")
    for d in divs:
        p     = len(d.findAll("p"))
        img   = len(d.findAll("img"))
        li    = len(d.findAll("li"))
        a     = len(d.findAll("a"))
        embed = len(d.findAll("embed"))
        pre   = len(d.findAll("pre"))
        code  = len(d.findAll("code"))
    
        if (d.renderContents().count(",") < 10):
            if ((pre == 0) and (code == 0)):
                if ((img > p ) or (li > p) or (a > p) or (p == 0) or (embed > 0)):
                    d.extract()
    

def upgradeLink(link):
    
    link = link.encode('utf-8')
    
    if (not (link.startswith("http://news.ycombinator.com") or link.endswith(".pdf"))):
        linkFile = "upgraded/" + re.sub(PUNCTUATION, "_", link)
        if (os.path.exists(linkFile)):
            return open(linkFile).read()
        else:
            content = ""
            try:
                html = urllib.urlopen(link).read()
                content = grabContent(link, html)
                filp = open(linkFile, "w")
                filp.write(content)
                filp.close()
            except IOError:
                pass
            except UnicodeDecodeError:
                pass
            return content
    else:
        return ""
    
    

def upgradeFeed(feedUrl):
    
    feedData = urllib.urlopen(feedUrl).read()
    
    upgradedLinks = []
    parsedFeed = feedparser.parse(feedData)
    
    for entry in parsedFeed.entries:
        upgradedLinks.append((entry, upgradeLink(entry.link)))
        
    rss = """<rss version="2.0">
<channel>
	<title>Hacker News</title>
	<link>http://news.ycombinator.com/</link>
	<description>Links for the intellectually curious, ranked by readers.</description>
	
    """

    for entry, content in upgradedLinks:
        rss += u"""
    <item>
        <title>%s</title>
        <link>%s</link>
        <comments>%s</comments>
        <description>
            <![CDATA[<a href="%s">Comments</a><br/>%s<br/><a href="%s">Comments</a>]]>
        </description>
    </item>
""" % (entry.title, escape(entry.link), escape(entry.comments), entry.comments, content.decode('utf-8'), entry.comments)

    rss += """
</channel>
</rss>"""


    return rss
    
if __name__ == "__main__":  
    print upgradeFeed(HN_RSS_FEED)
