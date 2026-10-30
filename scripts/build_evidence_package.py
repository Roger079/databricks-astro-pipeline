"""Generate a concise, three-page presentation evidence brief from saved evidence."""
import json
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.enums import TA_LEFT

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf/taco_bueno_presentation_evidence.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
real = json.loads((ROOT/'docs/evidence/normalized-real-verification.json').read_text(encoding='utf-8'))
demo = json.loads((ROOT/'docs/evidence/normalized-demo-verification.json').read_text(encoding='utf-8'))
bi = json.loads((ROOT/'docs/evidence/promotion-bi-deployment.json').read_text(encoding='utf-8'))
m = real['metrics']['rows'][0]
q = bi['sql_validation']['quality']['rows'][0]
assert int(m['source_rows']) == int(m['silver_rows']) + int(m['quarantine_rows'])
assert int(m['identifiable_checks']) == int(m['published_checks']) + int(m['review_checks'])
assert demo['metrics']['rows'][0]['quarantine_rows'] == '1'
W, H = 612, 792
LEFT, WIDTH = 43, 526
INK, RED, GRAY = colors.HexColor('#202D39'), colors.HexColor('#B93631'), colors.HexColor('#5B6670')
PAPER = colors.HexColor('#F3F6F7')
c = canvas.Canvas(str(OUT), pagesize=(W,H))
c.setTitle('Taco Bueno | Presentation Evidence Brief')
c.setAuthor('Taco Bueno Datathon Team')
styles = {
 'body': ParagraphStyle('body', fontName='Helvetica', fontSize=10, leading=14, textColor=INK),
 'small': ParagraphStyle('small', fontName='Helvetica', fontSize=8, leading=11, textColor=GRAY),
 'cell': ParagraphStyle('cell', fontName='Helvetica', fontSize=9, leading=12, textColor=INK),
 'white': ParagraphStyle('white', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.white),
}
repo='https://github.com/Roger079/databricks-astro-pipeline/blob/main/'

def para(text, y, style='body', x=LEFT, width=WIDTH):
    p=Paragraph(text, styles[style]); _,h=p.wrap(width,H); p.drawOn(c,x,y-h); return y-h-9

def heading(text,y):
    c.setFillColor(RED); c.setFont('Helvetica-Bold',12); c.drawString(LEFT,y,text); return y-17

def start(number,title,sub):
    c.setFillColor(RED); c.rect(0,H-10,W,10,fill=1,stroke=0)
    c.setFillColor(GRAY); c.setFont('Helvetica-Bold',8)
    c.drawString(LEFT,755,'TACO BUENO  /  PRICING & PROMOTION ANALYTICS')
    c.setFillColor(INK); c.setFont('Helvetica-Bold',23); c.drawString(LEFT,718,title)
    return para(sub,699,'small')-8

def finish(number, sources, cue):
    c.setStrokeColor(colors.HexColor('#D7DEE2')); c.line(LEFT,100,W-LEFT,100)
    para('<b>Presenter cue:</b> '+cue,90,'small')
    para(sources,60,'small')
    c.setFont('Helvetica',8); c.setFillColor(GRAY)
    c.drawString(LEFT,22,'Evidence captured October 30, 2026 | Real extract: Dec 31, 2025 - Jan 1, 2026')
    c.drawRightString(W-LEFT,22,f'{number} / 3'); c.showPage()

def table(headers, rows, widths, y):
    data=[[Paragraph(t,styles['white']) for t in headers]]
    data += [[Paragraph(str(t),styles['cell']) for t in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),INK), ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[PAPER,colors.white]),
        ('LINEBELOW',(0,-1),(-1,-1),.5,colors.HexColor('#D7DEE2'))]))
    _,h=t.wrap(WIDTH,H); t.drawOn(c,LEFT,y-h); return y-h-16

def link(path,label):
    return f'<link href="{repo+path}" color="#245D86">{label}</link>'

y=start(1,'From POS records to trusted data',
 'Presentation evidence brief | Three pages | Suggested walkthrough: about 5 minutes')
y=para('<b>Purpose:</b> build reliable evidence for pricing and promotion decisions. The current two-day extract demonstrates the complete pipeline; it does not yet establish promotion effects.',y)
y=heading('1  Pipeline: what each stage contributes',y-4)
y=table(['Stage','Contribution'],[
 ('Source / Bronze','Snapshot of an existing POS table; pinned Delta version 1, source identity and ingestion timestamp. Batch table-to-table ingestion.'),
 ('Silver','Parse and standardize records; classify items and adjustments; reconcile each ticket using store/date-specific financial rules. Separate quarantine and financial review.'),
 ('Gold','Publish reconciled daily, hourly, store and channel metrics; item/category units; source quality and ticket coverage.'),
 ('Dashboard / Genie','Six dashboard tabs and curated Q&A connect validated data to findings, investigations and next experiments.')
 ],[102,424],y)
y=para('<b>Execution proof:</b> Ingest -&gt; Transform -&gt; Validate -&gt; Analyze all succeeded. Real rerun <b>435278296555206</b> reproduced the first run\'s business totals from the same source version.',y)
y=heading('2  Transformations: three examples to explain',y-4)
y=table(['Before','After / why it matters'],[
 ('Ticket totals repeat on item rows','One published ticket per store + business date + check number. Repeated header amounts are counted once; legitimate repeated items remain.'),
 ('Source Total has two meanings','Profile A: customer = Total. Profile B: customer = Total - ticket discount + Tax. Both produce comparable customer and merchandise amounts.'),
 ('Voids, components and promo adjustments','Classify by role rather than delete indiscriminately. Zero-quantity components and void/promo adjustments do not inflate sold units.')
 ],[192,334],y)
y=para('<b>Illustrative arithmetic:</b> two item rows repeating a ticket total of 10.80 represent <b>10.80</b>, not 21.60. This is an explanation of the rule, not an extracted receipt.',y,'small')
assert y>111,y
finish(1,'Evidence: '+link('resources/jobs/daily_orchestration_job.yml','job definition')+' | '+link('docs/evidence/normalized-real-verification.json','real run and snapshot')+' | '+link('src/transformations/silver/mv_pos_checks.py','ticket rules'),
 'Explain the flow, then use repeated totals to show why cleaning changes the answer. (~90 seconds)')

y=start(2,'Quality checks with visible outcomes',
 'Distinguish source records, identifiable tickets, published tickets and financial exceptions.')
y=heading('3  Quality scorecard',y)
y=table(['Dimension','Check and verified evidence'],[
 ('Completeness','284,428 Bronze = 284,428 valid Silver + 0 structural quarantine. All 40,306 identifiable tickets are classified. This proves processing completeness for the extract, not completeness of all original sales.'),
 ('Consistency','40,306 identifiable = 40,257 published + 49 review. Daily aggregates reconcile by store/date; hourly and channel totals reconcile to published checks.'),
 ('Validity','Date/type, duration and known-profile checks. Synthetic demo: 12 source rows = 11 valid + 1 quarantined; an invalid date demonstrates rejection even though real quarantine is empty.'),
 ('Uniqueness','Published ticket key checked for duplicates. Repeated item rows are retained; unexplained monetary effects are checked through ticket reconciliation.'),
 ('Accuracy checks','Store-specific equations and customer = merchandise + tax checked. 39 equation exceptions occur within the 49 review tickets. This is arithmetic validation, not external receipt or settlement verification.')
 ],[101,425],y)
y=para('<b>Publication coverage: 99.87843%.</b> The 49 review tickets are withheld from published business metrics. Exception reasons can overlap; do not add them as separate totals.',y)
y=heading('Limits disclosed rather than hidden',y-3)
y=para(f'<b>Payment type:</b> all {int(q["unknown_payment_rows"]):,} normalized rows are Unknown; payment-method analysis is unsupported until source/mapping is confirmed.<br/>'
 f'<b>Item/category:</b> {int(q["missing_menu_item_rows"]):,} missing item names and {int(q["unknown_category_rows"]):,} unknown category rows.<br/>'
 f'<b>Duration:</b> {int(q["missing_duration_rows"]):,} rows have no usable duration and do not contribute valid durations; 23 overnight cases are marked assumptions.',y)
y=para('<b>Test evidence:</b> 28 local tests pass, including conflicting totals, repeated items, discounts, partial voids, unknown profiles and duration edge cases. Live run evidence also records Lakeflow expectations and successful validation.',y)
assert y>111,y
finish(2,'Evidence: '+link('notebooks/03_validate.py','live validation checks')+' | '+link('tests/test_pipeline.py','automated tests')+' | '+link('docs/evidence/normalized-demo-verification.json','synthetic failure case'),
 'Show row accounting and ticket accounting separately. A zero real quarantine count does not mean rejection was untested. (~90 seconds)')

y=start(3,'Findings that lead to useful actions',
 'Descriptive evidence from 114 stores across two holiday dates; amounts are in source monetary units.')
y=heading('4  Analysis: three findings to present',y)
y=para('<b>1. More transactions, smaller average basket.</b> Published tickets increased from 16,017 to 24,240 (<b>+51.34%</b>), while average customer amount per ticket fell from <b>16.32 to 14.62</b>. Action: separate volume from basket value when explaining performance.',y)
# Compact vector charts with independent, labeled scales.
top=y-8
for x,title,values,maximum,labels in [
    (LEFT,'Published tickets',[16017,24240],27000,['16,017','24,240']),
    (LEFT+275,'Average ticket',[261359.34/16017,354487.34/24240],18,['16.32','14.62'])]:
    c.setFont('Helvetica-Bold',10); c.setFillColor(INK); c.drawString(x,top,title)
    for i,(val,label) in enumerate(zip(values,labels)):
        yy=top-28-i*31
        c.setFont('Helvetica',8);c.setFillColor(GRAY);c.drawString(x,yy+5,['Dec 31','Jan 01'][i])
        c.setFillColor([colors.HexColor('#B7C7CD'),RED][i]);c.rect(x+40,yy,140*val/maximum,16,fill=1,stroke=0)
        c.setFillColor(INK);c.drawString(x+45+140*val/maximum,yy+4,label)
y=top-100
y=para('<b>2. Financial normalization matters.</b> Among published checks, mixed-definition source totals sum to <b>605,737.62</b>, while normalized customer amount is <b>615,846.68</b>. Action: compare stores using consistent customer or merchandise metrics, never the mixed raw Total.',y)
y=para('<b>3. High coverage with explicit exceptions.</b> <b>40,257</b> tickets are published and <b>49</b> remain visible for review. Action: investigate those exceptions without silently correcting values or hiding exclusions.',y)
y=table(['Published metric','Value'],[
 ('Customer amount including tax','615,846.68'),
 ('Merchandise after discounts, excluding tax','571,874.16'),
 ('Weighted average ticket across both dates','15.30')],[385,141],y)
y=heading('What we can recommend today',y-2)
y=para('Investigate financial exceptions and discount cohorts; design a controlled promotion test. Keep/stop/return rankings, promotion lift, seasonality and causal cannibalization require validated history, identifiable offers and a defensible baseline. No margin or ROI without costs.',y)
y=para('<b>Demo route:</b> Business overview -&gt; Pricing and discounts -&gt; Decisions -&gt; Trust. Dashboard SQL (11 datasets, 24 data widgets) and two Genie answers were verified. Browser layout, filters and another member\'s session still need a visual check.',y,'small')
y=para('<link href="'+bi['dashboard_url']+'" color="#245D86">Open published dashboard</link> | <link href="'+bi['genie_url']+'" color="#245D86">Open connected Genie space</link>',y,'small')
assert y>111,y
finish(3,'Evidence: '+link('validation/final_analysis.sql','reproducible analysis')+' | '+link('docs/findings.md','findings and daily comparison')+' | '+link('docs/evidence/promotion-bi-deployment.json','BI validation'),
 'Explain the volume/basket tradeoff, give the action, and finish with the boundary on promotion claims. (~2 minutes)')
c.save()
print(OUT)
