# Project: The Historical Court (Multi-Agent System)

## 📌 อธิบายโปรเจกต์ (Project Overview)
โปรเจกต์นี้คือระบบ Multi-Agent ที่พัฒนาด้วย **Google ADK (Agent Development Kit)** เพื่อทำงานในรูปแบบ "ศาลจำลอง" สำหรับวิเคราะห์บุคคลหรือเหตุการณ์ทางประวัติศาสตร์ โดยระบบจะทำการสืบค้นข้อมูลจาก Wikipedia ในแง่มุมที่ขัดแย้งกัน นำมาตรวจสอบความสมดุลของข้อมูลผ่านศาลก่อนจะสรุปผลออกมาเป็นรายงานที่เป็นกลางที่สุด

---

## 🤖 โครงสร้างของ Agent (Agent Architecture)
ระบบถูกออกแบบโดยแบ่งการทำงานออกเป็น 4 ขั้นตอนหลัก ดังต่อไปนี้:

### Step 1: The Inquiry (Sequential)
* **Agent:** `root_agent` (Host/Greeter)
* **หน้าที่:** ทักทายและรับชื่อหัวข้อจากผู้ใช้งาน 
* **กลไก:** เมื่อได้รับคำตอบ จะใช้ Tool `append_to_state` เพื่อบันทึกข้อมูลลงใน Session State ที่ Key `PROMPT` และส่งต่อให้ทีมวิเคราะห์

### Step 2: The Investigation (Parallel)
การค้นหาข้อมูลแบบคู่ขนานเพื่อหาข้อโต้แย้งจาก 2 ฝั่ง โดยใช้ `ParallelAgent` (`investigation_team`):
* **Agent A: The Admirer (`admirer_agent`)**
  * **หน้าที่:** ค้นหาและรวบรวมข้อมูลด้านบวก ความสำเร็จ และผลงานที่โดดเด่น
  * **กลไก:** ใช้ `wiki_tool` ค้นหาข้อมูลโดยเติม Keyword เช่น *achievements* หรือ *legacy* และบันทึกผลลัพธ์ลง Session State ใน Key `pos_data`
* **Agent B: The Critic (`critic_agent`)**
  * **หน้าที่:** ค้นหาและรวบรวมข้อมูลด้านลบ ข้อผิดพลาด และข้อโต้แย้ง
  * **กลไก:** ใช้ `wiki_tool` ค้นหาข้อมูลโดยเติม Keyword เช่น *controversy* หรือ *criticisms* และบันทึกผลลัพธ์ลง Session State ใน Key `neg_data`

### Step 3: The Trial & Review (Loop)
การวนลูปตรวจสอบข้อมูลเพื่อความสมบูรณ์ของเนื้อหา โดยใช้ `LoopAgent` (`trial_loop`):
* **Agent C: The Judge (`judge_logic_agent`)**
  * **หน้าที่:** ตรวจสอบความสมดุลของข้อมูลใน State ระหว่าง `pos_data` และ `neg_data`
  * **กลไก:** * หากข้อมูลฝั่งใดฝั่งหนึ่งน้อยเกินไปหรือว่างเปล่า ศาลจะไม่จบงาน แต่จะสั่งให้ `investigation_team` กลับไปค้นหาใหม่
    * หากข้อมูลครบถ้วนและสมดุลแล้ว ศาลจะยุติการโต้เถียงโดยเรียกใช้ Tool **`exit_loop`** เท่านั้น เพื่อหลุดออกจากลูป

### Step 4: The Verdict (Output)
* **Agent:** `verdict_agent` (Final Reporter)
* **หน้าที่:** สรุปรายงานเปรียบเทียบข้อเท็จจริงทั้งหมดที่ผ่านการพิจารณาจากศาล
* **กลไก:** ประมวลผลข้อมูลจาก `PROMPT`, `pos_data`, และ `neg_data` เพื่อเขียนเป็นรายงานสรุปที่เป็นกลาง และใช้ Tool `write_file` บันทึกผลลัพธ์ลงในไฟล์ `verdict_report.txt`

---

## 🛠️ เครื่องมือที่ใช้งาน (Tools Used)
1. **`append_to_state`**: สำหรับจัดการ Session State และแชร์ข้อมูลระหว่าง Agent
2. **`LangchainTool (WikipediaQueryRun)`**: สำหรับดึงข้อมูลข้อเท็จจริงจาก Wikipedia
3. **`exit_loop`**: สำหรับใช้ควบคุมเงื่อนไขการหลุดออกจาก LoopAgent อย่างถูกต้อง
4. **`write_file`**: สำหรับบันทึกผลลัพธ์ขั้นสุดท้ายออกเป็นไฟล์ Text (.txt)
