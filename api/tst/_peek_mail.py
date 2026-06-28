import json, re, urllib.request
MAIL="http://127.0.0.1:8025"
msgs=json.loads(urllib.request.urlopen(MAIL+"/api/v1/messages").read())
for m in msgs["messages"]:
    if "Verify your email" in m.get("Subject",""):
        msg=json.loads(urllib.request.urlopen(f"{MAIL}/api/v1/message/{m['ID']}").read())
        to=msg["To"][0]["Address"]
        text=(msg.get("Text") or "")+(msg.get("HTML") or "")
        print("TO", to)
        print("tokens", re.findall(r"token[=/\"']([A-Za-z0-9._-]+)", text)[:5])
        print("snippet", text[:500])
        break
