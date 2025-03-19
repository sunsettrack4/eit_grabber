import datetime, json, os, sqlite3, sys, time, xmltodict

try:
    if "days=" in sys.argv[1]:
        days = int(sys.argv[1].split("=")[1])
except:
    days = 30


#
# CREATE DATABASE
#

try:
    os.mkdir(f"{os.getcwd()}/scan-db")
except:
    pass

while True:

    conn = sqlite3.connect(f"{os.getcwd()}/scan-db/epg.db", check_same_thread=False)
    c = conn.cursor()

    final_files = [i for i in os.listdir(f"{os.getcwd()}/scan-files") if "_final" in i]

    for i in final_files:

        c.execute("""CREATE TABLE IF NOT EXISTS {}"""
                """(ts_id INTEGER, service_id INTEGER, event_id INTEGER, broadcast_id TEXT PRIMARY KEY, start INTEGER, end INTEGER,"""
                """ name TEXT, text TEXT, desc TEXT, table_id INTEGER)""".format(f"pre_{i.replace('_final', '')}"))
        c.execute("""DELETE FROM {}""".format(f"pre_{i.replace('_final', '')}"))
        conn.commit()
        c.execute("""VACUUM""")

        with open(f"{os.getcwd()}/scan-files/{i}", "rb") as file:
            for line_b in file:
                line = line_b.replace(b'\xc2\x8a', b' --- ').decode()  # ARD - WORKAROUND
                
                if "[EIT]::store" in line:
                    l = line.split("[EIT]::store: ")[1].encode()
                    l = json.loads(l)

                    for e in l["events"]:
                        desc = ""
                        for d in e["descriptors"]:
                            if d["descriptorTag"] == 77:
                                name = d["name"].replace('\\"', "")
                                text = d["text"].replace('\\"', "")

                                # P7S1 - WORKAROUND FOR MISSING NEWLINES (dvbtee bug)
                                if l["serviceId"] in [61300, 61301, 61302, 61303, 61304, 61305, 61322, 61323, 61324, 61325]:          
                                    if "Altersfreigabe: " in text:
                                        text = text.split("Altersfreigabe: ")[0] + "\n" + "Altersfreigabe: " + text.split("Altersfreigabe: ")[1]
                                    if "(WH vom" in text:
                                        text = text.split("(WH vom")[0] + "\n" + "(WH vom" + text.split("(WH vom")[1]                      
                                    
                                    sub = text.split("\n")[0]
                                    le = None
                                    for n, k in enumerate(sub[::-1]):
                                        if not le:
                                            le = k
                                            continue
                                        if (le.isupper()) and (k.islower() or k.isnumeric() or k in ["!", "?", "."]):
                                            new_text = sub[::-1][n:][::-1] + "\n" + sub[::-1][:n][::-1]
                                            text = new_text + "\n" + "\n".join(text.split("\n")[1:])
                                            break
                                        le = k
                                    
                                c.execute("""INSERT OR REPLACE INTO {} """
                                        """(ts_id, service_id, event_id, broadcast_id, start, end, name, text, desc, table_id)"""
                                        """VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""".format(f"pre_{i.replace('_final', '')}"),
                                        (l["tsId"], l["serviceId"], e["eventId"], str(l["serviceId"])+"_"+str(e["eventId"]), e["unixTimeBegin"], e["unixTimeEnd"], name, text, "", l["tableId"]))
                                conn.commit()
                            if d["descriptorTag"] == 78:
                                desc = desc + d["text"]
                        
                        if desc != "":
                            desc = desc.replace(" --- ", "\n")  # ARD - WORKAROUND
                            desc = desc.replace("<ul><li>", "* ").replace("</li></ul>", "").replace("</li><li>", "\n* ")  # ARD - WORKAROUND
                            desc = desc.replace('\\"', '"')

                            # P7S1 - WORKAROUND FOR MISSING NEWLINES (dvbtee bug)
                            def return_actors(sub, type):
                                actors = []
                                le = None
                                sub_text = ""
                                replace_text = ""
                                space_counter = 0
                                for n, k in enumerate(sub[::-1]):
                                    if k == " ":
                                        space_counter =+ 1
                                    if not le:
                                        le = k
                                        continue
                                    if (le.isupper() and (k.islower() or k.isnumeric() or k in ["!", "?", "."])) and space_counter >= 1:
                                        new_text = sub[::-1][:n][::-1].replace(replace_text, "")
                                        sub_text = sub_text + ("\n" if sub_text != "" else "") + new_text.replace(sub_text.replace("\n", ""), "")
                                        actors.insert(0, new_text)
                                        replace_text = new_text + replace_text
                                        space_counter = 0
                                    le = k
                                new_text = sub[::-1][:n+1][::-1].replace(replace_text, "")
                                actors.insert(0, new_text)
                                return desc.split(type)[0] + "\n\n" + type + "\n" + "\n".join(actors)

                            if l["serviceId"] in [61300, 61301, 61302, 61303, 61304, 61305, 61322, 61323, 61324, 61325]:
                                desc = desc.replace("sixx", "SIXX")
                                if len(desc) >= 12 and "Moderation: " in desc[0:12]:
                                    le = None
                                    for n, k in enumerate(desc):
                                        if not le:
                                            le = k
                                            continue
                                        if (k.isupper()) and (le.islower() or le.isnumeric() or le in ["!", "?", "."]):
                                            desc = desc[:n] + "\n\n" + desc[n:]
                                            break
                                        le = k

                                if "Regie: " in desc:
                                    desc = desc.split("Regie: ")[0] + ("\n" if desc.split("Regie: ")[0][-1] not in [" ", ".", "?", "!"] else "\n\n") + "Regie: " + desc.split("Regie: ")[1] + " "
                                if "Drehbuch: " in desc:
                                    desc = desc.split("Drehbuch: ")[0] + ("\n" if desc.split("Drehbuch: ")[0][-1] not in [" ", ".", "?", "!"] else "\n\n") + "Drehbuch: " + desc.split("Drehbuch: ")[1] + " "
                                if "Autor: " in desc:
                                    desc = desc.split("Autor: ")[0] + ("\n" if desc.split("Autor: ")[0][-1] not in [" ", ".", "?", "!"] else "\n\n") + "Autor: " + desc.split("Autor: ")[1] + " "
                                if "Komponist: " in desc:
                                    desc = desc.split("Komponist: ")[0] + ("\n" if desc.split("Komponist: ")[0][-1] not in [" ", ".", "?", "!"] else "\n\n") + "Komponist: " + desc.split("Komponist: ")[1] + " "
                                if "Kamera: " in desc:
                                    desc = desc.split("Kamera: ")[0] + ("\n" if desc.split("Kamera: ")[0][-1] not in [" ", ".", "?", "!"] else "\n\n") + "Kamera: " + desc.split("Kamera: ")[1] + " "
                                if "Schnitt: " in desc:
                                    desc = desc.split("Schnitt: ")[0] + ("\n" if desc.split("Schnitt: ")[0][-1] not in [" ", ".", "?", "!"] else "\n\n") + "Schnitt: " + desc.split("Schnitt: ")[1] + " "
                                if "Animation: " in desc:
                                    desc = desc.split("Animation: ")[0] + ("\n" if desc.split("Animation: ")[0][-1] not in [" ", ".", "?", "!"] else "\n\n") + "Animation: " + desc.split("Animation: ")[1] + " "
                                if "Gastgeber: " in desc:
                                    desc = desc.split("Gastgeber: ")[0] + ("\n" if desc.split("Gastgeber: ")[0][-1] not in [" ", ".", "?", "!"] else "\n\n") + "Gastgeber: " + desc.split("Gastgeber: ")[1] + " "
                                if "Kommentar: " in desc:
                                    desc = desc.split("Kommentar: ")[0] + ("\n" if desc.split("Kommentar: ")[0][-1] not in [" ", ".", "?", "!"] else "\n\n") + "Kommentar: " + desc.split("Kommentar: ")[1] + " "
                                if "Experte: " in desc:
                                    desc = desc.split("Experte: ")[0] + ("\n" if desc.split("Experte: ")[0][-1] not in [" ", ".", "?", "!"] else "\n\n") + "Experte: " + desc.split("Experte: ")[1] + " "
                                if "Darsteller:" in desc and desc.split("Darsteller:")[1][0] != " ":
                                    if ")" in desc.split("Darsteller:")[1]:
                                        desc = desc.split("Darsteller:")[0] + "\n\n" + "Darsteller:\n" + ")\n".join(desc.split("Darsteller:")[1].split(")"))
                                    else:
                                        desc = return_actors(desc.split("Darsteller:")[1], "Darsteller:")
                                if "Mitwirkende:" in desc and desc.split("Mitwirkende:")[1][0] != " ":
                                    desc = return_actors(desc.split("Mitwirkende:")[1], "Mitwirkende:")
                            
                            c.execute("""UPDATE pre_{} SET desc = ? WHERE broadcast_id = ?""".format(i.replace('_final', '', )), (str(desc), str(l["serviceId"])+"_"+str(e["eventId"])))    
                            conn.commit()

                        c.execute("SELECT service_id FROM {}".format((f"pre_{i.replace('_final', '')}")))
                        service_ids = list(set([i[0] for i in c.fetchall()]))

        for s in service_ids:
            
            c.execute("""SELECT start, broadcast_id, table_id FROM pre_{} WHERE service_id = ?""".format(i.replace('_final', '')), [s])
            starts = sorted(i for i in c.fetchall())
            c.execute("""SELECT end, broadcast_id, table_id FROM pre_{} WHERE service_id = ?""".format(i.replace('_final', '')), [s])
            ends = sorted(i for i in c.fetchall())

            num = len(starts)
            for j in range(1, num):
                if j+1 == num:
                    break
            
                if starts[j+1][0] == ends[j][0]:
                    continue
                else:
                    if starts[j+1][2] == ends[j][2]:
                        c.execute("""UPDATE pre_{} SET end = ? WHERE broadcast_id = ?""".format(i.replace('_final', '', )), (starts[j+1][0], ends[j][1]))
                        conn.commit()
                        print(f"WARNING: service_id {str(s)}, broadcast_id {str(ends[j][1])} - Broadcast duration increased")
                    else:
                        print(f"WARNING: service_id {str(s)}, broadcast_id {str(ends[j][1])} - Missing tables detected, scan time needs to be increased")

        os.remove(f"{os.getcwd()}/scan-files/{i}")


    #
    # CREATE XML FILE
    #

    if not final_files:
        c.close()
        time.sleep(60)
        continue

    c.execute("SELECT name FROM sqlite_master WHERE type='table';")

    try:
        tables = [i[0] for i in c.fetchall()] 
    except:
        pass

    with open(f"{os.getcwd()}/pre_guide.xml", "w", encoding="UTF-8") as file:
        
        # GENERAL INFO
        file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        file.write('<tv>\n')

        for t in tables:
            c.execute("SELECT service_id FROM {}".format(t))
            service_ids = list(set([i[0] for i in c.fetchall()]))

            # CHANNEL LIST
            ch = {"channel": []}
            for s in service_ids:
                ch_part = {"@id": str(s), "display-name": str(s)}
                ch["channel"].append(ch_part)
            file.write(xmltodict.unparse(ch, pretty=True, encoding="UTF-8", full_document=False))

        for t in tables:
            c.execute("SELECT service_id FROM {}".format(t))
            service_ids = list(set([i[0] for i in c.fetchall()]))

            # PROGRAMMES
            allowed_desc = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=days)
            for s in service_ids:
                c.execute("""SELECT service_id, start, end, name, text, desc FROM {} WHERE service_id = ? ORDER BY start ASC""".format(t), [s])
                p = c.fetchall()

                pr = {"programme": []}

                for q in p:
                    program = {"@start": datetime.datetime.fromtimestamp(float(q[1]), datetime.UTC).strftime("%Y%m%d%H%M%S +0000"), "@stop": datetime.datetime.fromtimestamp(float(q[2]), datetime.UTC).strftime("%Y%m%d%H%M%S +0000"), "@channel": str(q[0])}
                    
                    program["title"] = str(q[3])

                    if q[4] is not None and str(q[4]) != "":
                        program["sub-title"] = str(q[4])

                    if datetime.datetime.fromtimestamp(float(q[1]), datetime.UTC) < allowed_desc:
                        if q[5] is not None and str(q[5]) != "":
                            program["desc"] = str(q[5])

                    pr["programme"].append(program)

                file.write(xmltodict.unparse(pr, pretty=True, encoding="UTF-8", full_document=False))

        file.write('</tv>\n')

    c.close()
    os.rename(f"{os.getcwd()}/pre_guide.xml", f"{os.getcwd()}/guide.xml")
    time.sleep(60)