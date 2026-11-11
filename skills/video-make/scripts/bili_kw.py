import sys, json, urllib.request, urllib.parse, http.cookiejar, time, re
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
cj=http.cookiejar.CookieJar()
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders=[("User-Agent",UA)]
op.open("https://www.bilibili.com/",timeout=20).read()
for kw in sys.argv[1:]:
    u="https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword="+urllib.parse.quote(kw)
    r=urllib.request.Request(u,headers={"Referer":"https://search.bilibili.com/","User-Agent":UA})
    d=json.loads(op.open(r,timeout=20).read())
    res=(d.get("data") or {}).get("result") or []
    print("==",kw,"total",(d.get("data") or {}).get("numResults"))
    for v in res[:6]:
        t=re.sub("<[^>]+>","",v["title"])
        print("  %7s  %s  %s  %s"%(v["play"],time.strftime("%Y-%m",time.localtime(v["pubdate"])),v["duration"],t[:50]))
    time.sleep(1.2)
