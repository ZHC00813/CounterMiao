import re,json,hashlib,uuid,zipfile,shutil,os
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from xml.sax.saxutils import escape
import legacy

KINDS=['零星采购','服务采购','物资采购','差旅报销']
REQUIRED={'零星采购':[], '服务采购':['服务类采购申请'], '物资采购':['采购申请或审批','采购入库材料'], '差旅报销':['行程单','行程申请','调研申请']}
RULES={'零星采购':'同供应商同自然月累计≤1000元；每单≤5000元、15项；必需：发票＋签字验收单', '服务采购':'一票一份验收单；单票≤5000元、最多15项；必需：服务类采购申请＋签字验收单', '物资采购':'单票及每份验收单≤5000元、最多15项；必需：采购申请/审批＋入库材料＋签字验收单','差旅报销':'金额及明细数量不限；无需图片/采购验收单；必需：发票、行程单、行程申请、调研申请'}
def uid():return uuid.uuid4().hex
def project(name,kind=None):
    result=dict(id=uid(),name=name,manual_complete=False,types={k:dict(invoices=[],attachments={},signed={}) for k in KINDS})
    if kind is not None:
        if kind not in KINDS:raise ValueError('请选择有效的报销类型')
        result['kind']=kind
    return result
def parent_kind(p):
    if p.get('kind') in KINDS:return p['kind']
    existing={e['kind'] for e in p.get('entries',[])}|{k for k,t in p['types'].items() if t['invoices'] or t.get('attachments')}
    if len(existing)==1:p['kind']=next(iter(existing));return p['kind']
    return None
def add_entry(p,name):
    kind=parent_kind(p)
    if not kind:raise ValueError('请先新建并选择类型明确的报销项；旧版混合类型数据保持原样')
    if not name.strip():raise ValueError('请填写报销条目名称')
    e=entry(name.strip(),kind);p.setdefault('entries',[]).append(e);sync(p);return e
def entry(name,kind):return dict(id=uid(),name=name,kind=kind,invoices=[],attachments={},red=False,hidden=False)
def ensure_entries(p):
    parent_kind(p)
    if p.get('entries'):return
    p.setdefault('entries',[])
    for kind,t in p['types'].items():
        if t['invoices'] or t.get('attachments'):
            e=entry(kind+'报销项',kind);e['invoices']=t['invoices'];e['attachments']=t.get('attachments',{});p['entries'].append(e)
    sync(p)
def sync(p):
    if not p.get('entries'):return
    for kind in KINDS:p['types'][kind]['invoices']=[]
    for e in p['entries']:
        for i in e['invoices']:i['entry_id']=e['id'];i['entry_name']=e['name']
        p['types'][e['kind']]['invoices'].extend(e['invoices'])
def identity(inv):return inv.get('number') or inv.get('hash') or inv['source']
def supplier(inv):
    tax=re.sub(r'\s','',inv.get('seller_tax','')).upper()
    name=re.sub(r'[\s（）()]','',inv.get('seller','')).casefold()
    return '税号:'+tax if tax else ('名称:'+name if name else '')
def month(inv):
    raw=inv.get('date','').strip();dt=datetime.strptime(raw,'%Y-%m-%d')
    return dt.strftime('%Y-%m')
def all_invoices(projects):
    for p in projects:
        for kind,t in p['types'].items():
            for inv in t['invoices']:yield p,kind,inv
def monthly_issues(projects):
    groups={};problems={};aliases={}
    for _,kind,i in all_invoices(projects):
        if kind=='零星采购' and i.get('seller') and i.get('seller_tax'):
            n=re.sub(r'[\s（）()]','',i['seller']).casefold();aliases.setdefault(n,set()).add(supplier(i))
    seen=set()
    for p,kind,i in all_invoices(projects):
        if kind!='零星采购':continue
        key=identity(i)
        try:
            sup=supplier(i)
            if not sup:raise ValueError('请补充销售方名称或税号')
            if not i.get('seller_tax'):
                name=re.sub(r'[\s（）()]','',i.get('seller','')).casefold();matches=aliases.get(name,set())
                if len(matches)>1:raise ValueError('同名销售方对应多个税号，请核对税号')
                if len(matches)==1:sup=next(iter(matches))
            ym=month(i);amount=legacy.money(i['amount'])
            if key not in seen:groups.setdefault((sup,ym),[]).append((key,amount));seen.add(key)
        except Exception as e:problems[key]=str(e)
    for (sup,ym),rows in groups.items():
        total=sum((v for _,v in rows),Decimal(0))
        if total>1000:
            for key,_ in rows:problems[key]=f'{ym} 同供应商累计 {total:.2f} 元，超过1000元（跨项目）'
    return problems
def check_invoice(inv,kind):
    if not inv.get('number'):raise ValueError('请补充发票号码')
    if not inv.get('confirmed'):raise ValueError('发票尚未核对确认')
    if not readable(inv.get('source','')):raise ValueError('原发票缺失、为空或不可读取')
    amount=legacy.money(inv.get('amount',''))
    if kind=='差旅报销':return
    checked=dict(inv);checked['photos']=[];legacy.validate(checked)
    if kind=='零星采购' and amount>1000:raise ValueError('零星采购单票超过1000元')
    if amount>5000:raise ValueError('单票超过5000元，不自动拆票')
    if len(inv['items'])>15:raise ValueError('单票采购项目超过15项，不自动拆票')
def plan(projects,p,kind):
    batches=[];blocked=[];issues=monthly_issues(projects)
    invoices=p['types'][kind]['invoices']
    for i in sorted(invoices,key=lambda x:safe_amount(x),reverse=True):
        try:
            check_invoice(i,kind)
            if kind=='零星采购' and identity(i) in issues:raise ValueError(issues[identity(i)])
        except Exception as e:blocked.append((i,str(e)));continue
        amount=legacy.money(i['amount']);count=len(i.get('items',[]))
        if kind=='差旅报销':count=1
        for b in batches:
            if kind!='服务采购' and (kind=='差旅报销' or (b['amount']+amount<=5000 and b['count']+count<=15)) and b['category']==i.get('category','采购'):
                b['invoices'].append(i);b['amount']+=amount;b['count']+=count;break
        else:batches.append(dict(invoices=[i],amount=amount,count=count,category=i.get('category','采购')))
    for b in batches:
        payload=[{k:v for k,v in inv.items() if k not in ['text','source','photos','hash','entry_id','entry_name']} for inv in b['invoices']]
        payload=sorted(payload,key=lambda x:identity(x))
        b['id']=hashlib.sha256(json.dumps([kind,payload],ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:16]
    return batches,blocked
def safe_amount(i):
    try:return legacy.money(i.get('amount',''))
    except Exception:return Decimal(-1)
def readable(path):
    try:
        p=Path(path)
        if not path or not p.is_file() or p.stat().st_size==0:return False
        with p.open('rb') as f:f.read(1)
        return True
    except OSError:return False
def inspect_project(projects,p):
    errors=[];details=[];seen={}
    for op,kind,inv in all_invoices(projects):
        key=identity(inv)
        if key in seen and (op['id']==p['id'] or seen[key]==p['id']):errors.append('重复占用发票：'+key)
        seen[key]=op['id']
    for kind,t in p['types'].items():
        if not t['invoices']:
            if t.get('attachments') or t.get('signed'):errors.append(kind+'：有附件但没有发票')
            continue
        batches,blocked=plan(projects,p,kind)
        errors.extend(f'{kind} / {identity(i)}：{e}' for i,e in blocked)
        if not p.get('entries'):
            for key in REQUIRED[kind]:
                paths=t.get('attachments',{}).get(key,[])
                if not paths or any(not readable(v) for v in paths):errors.append(kind+'：缺少或无法读取 '+key)
        if kind!='差旅报销':
            for b in batches:
                scans=t.get('signed',{}).get(b['id'],[])
                if not scans or any(not readable(v) for v in scans):errors.append(f'{kind} / 验收单 {b["id"]}：缺少有效签字扫描件')
        details.append(dict(kind=kind,batches=batches))
    for e in p.get('entries',[]):
        if p.get('kind') in KINDS and e['kind']!=p['kind']:errors.append(e['name']+'：条目类型与所属报销项不一致')
        if not e.get('name','').strip():errors.append('报销项名称未填写')
        if not e['invoices']:continue
        for key in REQUIRED[e['kind']]:
            paths=e.get('attachments',{}).get(key,[])
            if not paths or any(not readable(v) for v in paths):errors.append(e['name']+'：缺少或无法读取 '+key)
    if not any(t['invoices'] for t in p['types'].values()):errors.append('项目没有发票')
    return list(dict.fromkeys(errors)),details
def safe_name(text):
    name=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',text).strip(' .')[:75] or '未命名'
    if name.upper().split('.')[0] in {'CON','PRN','AUX','NUL',*[f'COM{x}' for x in range(1,10)],*[f'LPT{x}' for x in range(1,10)]}:name='_'+name
    return name
def store_file(source,folder):
    source=Path(source)
    if not readable(str(source)):raise ValueError('文件不存在、为空或不可读：'+str(source))
    digest=hashlib.sha256(source.read_bytes()).hexdigest();folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    target=folder/(digest[:16]+'_'+safe_name(source.stem)[:65]+source.suffix.lower())
    if not target.exists():shutil.copy2(source,target)
    return str(target.resolve())

def xlsx(path,sheets):
    # Small deterministic OOXML writer: no external runtime required in the desktop app.
    ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    def col(n):
        s=''
        while n:n,r=divmod(n-1,26);s=chr(65+r)+s
        return s
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'+''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,len(sheets)+1))+'</Types>')
        z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml',f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'+''.join(f'<sheet name="{escape(name,{chr(34):"&quot;"})}" sheetId="{i}" r:id="rId{i}"/>' for i,(name,_) in enumerate(sheets,1))+'</sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(sheets)+1))+f'<Relationship Id="rId{len(sheets)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        colors=['217346','1F4E78','7030A0','9E480E','006666','7F1D1D']
        extra_fills=''.join(f'<fill><patternFill patternType="solid"><fgColor rgb="FF{color}"/></patternFill></fill>' for color in colors)
        extra_styles=''.join(f'<xf fontId="1" fillId="{n+3}" borderId="0" xfId="0"><alignment vertical="center" wrapText="1"/></xf>' for n in range(len(colors)))
        z.writestr('xl/styles.xml',f'<styleSheet xmlns="{ns}"><fonts count="2"><font><sz val="11"/><name val="Microsoft YaHei"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Microsoft YaHei"/></font></fonts><fills count="9"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF217346"/></patternFill></fill>{extra_fills}</fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="9"><xf fontId="0" fillId="0" borderId="0" xfId="0"><alignment vertical="top" wrapText="1"/></xf><xf fontId="1" fillId="2" borderId="0" xfId="0"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="4" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>{extra_styles}</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
        for i,(name,rows) in enumerate(sheets,1):
            content=[]
            for r,row in enumerate(rows,1):
                cells=[]
                for c,value in enumerate(row,1):
                    ref=f'{col(c)}{r}'
                    if isinstance(value,(Decimal,int)):cells.append(f'<c r="{ref}" s="2"><v>{value}</v></c>')
                    else:
                        text=''.join(ch for ch in str(value) if ord(ch)>=32 or ch in '\n\t')
                        cells.append(f'<c r="{ref}" t="inlineStr" s="{getattr(row,"style",1 if r==1 else 0)}"><is><t xml:space="preserve">{escape(text)}</t></is></c>')
                content.append(f'<row r="{r}" ht="34" customHeight="1">'+''.join(cells)+'</row>')
            z.writestr(f'xl/worksheets/sheet{i}.xml',f'<worksheet xmlns="{ns}"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols><col min="1" max="1" width="24" customWidth="1"/><col min="2" max="12" width="28" customWidth="1"/></cols><sheetData>'+''.join(content)+'</sheetData></worksheet>')

def travel_table(invoices,path):
    rows=[['发票号码','开票日期','销售方','费用说明','含税金额（元）']]
    for i in invoices:rows.append([i['number'],i.get('date',''),i.get('seller',''),i.get('purpose',''),legacy.money(i['amount'])])
    rows.append(['合计','','','',sum((legacy.money(i['amount']) for i in invoices),Decimal(0))]);xlsx(path,[('差旅报销表',rows)])
class Band(list):
    def __init__(self,values,style):super().__init__(values);self.style=style
def inventory_table(projects,path,batch_name,all_projects=None):
    rows=[['报销批次','报销项目 / 报销项','文件类别','发票号码 / 文件名','单体金额（元）','累计金额（元）','材料状态','文件位置','说明']]
    grand=Decimal(0);unknown=0
    for n,p in enumerate(projects):
        style=3+n%6;invoices=[i for t in p['types'].values() for i in t['invoices']];stats=legacy.amount_summary(invoices);grand+=stats['amount'];unknown+=stats['unknown']
        rows.append(Band([batch_name,'项目：'+p['name'],'项目总额','','',stats['amount'],'金额待识别 '+str(stats['unknown'])+' 张','',''],style))
        entries=p.get('entries',[])
        if not entries:
            ensure_entries(p);entries=p.get('entries',[])
        for e in entries:
            total=legacy.amount_summary(e['invoices']);rows.append(Band(['',e['name'],e['kind'],'报销项小计','',total['amount'],'','',''],style))
            for inv in e['invoices']:
                valid=readable(inv.get('source',''));rows.append(['',e['name'],'发票',inv.get('number',''),safe_amount(inv) if safe_amount(inv)>=0 else '待识别','','已有' if valid else '缺失',inv.get('source',''),inv.get('date','')+' '+inv.get('seller','')])
                for photo in inv.get('photos',[]):rows.append(['',e['name'],'配图（可选）',Path(photo).name,'','','已有' if readable(photo) else '原图片不存在',photo,'不影响必需材料检查'])
            for label in REQUIRED[e['kind']]:
                paths=e.get('attachments',{}).get(label,[])
                if not paths:rows.append(['',e['name'],label,'','','','缺失','','必需材料'])
                for file in paths:rows.append(['',e['name'],label,Path(file).name,'','','已有' if readable(file) else '缺失',file,''])
            for label,paths in e.get('attachments',{}).items():
                if label not in REQUIRED[e['kind']]:
                    for file in paths:rows.append(['',e['name'],label,Path(file).name,'','','已有' if readable(file) else '缺失',file,''])
            if e['kind']!='差旅报销':
                for b in plan(all_projects or projects,p,e['kind'])[0]:
                    if not any(i.get('entry_id')==e['id'] for i in b['invoices']):continue
                    paths=p['types'][e['kind']]['signed'].get(b['id'],[])
                    if not paths:rows.append(['',e['name'],'签字验收单',b['id'],'',b['amount'],'缺失','','对应规划验收单'])
                    for file in paths:rows.append(['',e['name'],'签字验收单',b['id'],'',b['amount'],'已有' if readable(file) else '缺失',file,''])
        errors,_=inspect_project(all_projects or projects,p)
        for error in errors:rows.append(['',p['name'],'检查问题','','','','待处理','',error])
    rows.append(['批次合计','','','','',grand,'另有金额待识别 '+str(unknown)+' 张','','']);xlsx(path,[('报销批次详细清单',rows)])
def export_all(projects,root):
    root=Path(root);dest=root/('待报销材料_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'));dest.mkdir()
    summary=[['项目','手动状态','自动检查','发票数','已识别金额（元）','问题']];details=[['项目','报销项','类型','发票号','金额（元）','开票日期','销售方','文件位置']];files=[['项目','类型','文件类别','归档位置']]
    manifest=dict(version=3,projects=[])
    for n,p in enumerate(projects,1):
        errors,plans=inspect_project(projects,p);folder=dest/f'{n:02}_{safe_name(p["name"])}';folder.mkdir();snap=json.loads(json.dumps(p))
        invoices=[i for t in p['types'].values() for i in t['invoices']];stats=legacy.amount_summary(invoices)
        summary.append([p['name'],'已完成' if p.get('manual_complete') else '整理中','通过' if not errors else '未通过',len(invoices),stats['amount'],'；'.join(errors)])
        def copy(src,sub,kind,label):
            out=store_file(src,folder/sub);relative=str(Path(out).relative_to(dest));files.append([p['name'],kind,label,relative]);return relative
        for kind,t in snap['types'].items():
            if not t['invoices'] and not t.get('attachments') and not t.get('signed'):continue
            for inv in t['invoices']:
                itemfolder=Path('报销项')/(safe_name(inv.get('entry_name',kind))+'_'+inv.get('entry_id','')[:6])
                if readable(inv['source']):inv['source']=copy(inv['source'],itemfolder/'发票',kind,'发票')
                else:inv['source']=''
                details.append([p['name'],inv.get('entry_name',''),kind,inv['number'],safe_amount(inv) if safe_amount(inv)>=0 else '',inv.get('date',''),inv.get('seller',''),inv['source']])
                pics=[]
                if kind!='差旅报销':
                    for path in inv.get('photos',[]):
                        if readable(path):pics.append(copy(path,itemfolder/'图片'/safe_name(identity(inv)),kind,'图片'))
                inv['photos']=pics
            for label,paths in t.get('attachments',{}).items():t['attachments'][label]=[copy(v,Path(kind)/safe_name(label),kind,label) for v in paths if readable(v)]
            for bid,paths in t.get('signed',{}).items():t['signed'][bid]=[copy(v,Path(kind)/'验收单签字扫描件'/bid,kind,'签字验收单 '+bid) for v in paths if readable(v)]
            batches,_=plan(projects,p,kind)
            if kind=='差旅报销':
                valid=[i for b in batches for i in b['invoices']]
                if valid:
                    (folder/kind).mkdir(parents=True,exist_ok=True);travel_table(valid,folder/kind/'差旅报销表.xlsx')
            else:
                for b in batches:
                    out=folder/kind/'验收单';out.mkdir(exist_ok=True,parents=True)
                    document_batch=dict(b);document_batch['invoices']=[dict(i,photos=[v for v in i.get('photos',[]) if readable(v)]) for i in b['invoices']]
                    legacy.build_doc(document_batch,out/f'验收单_{b["id"]}.docx')
        for e in snap.get('entries',[]):
            e['invoices']=[i for t in snap['types'].values() for i in t['invoices'] if i.get('entry_id')==e['id']]
            base=Path('报销项')/(safe_name(e['name'])+'_'+e['id'][:6])
            for label,paths in e.get('attachments',{}).items():e['attachments'][label]=[copy(v,base/safe_name(label),e['kind'],label) for v in paths if readable(v)]
        (folder/'材料检查.json').write_text(json.dumps(dict(问题=errors,通过=not errors),ensure_ascii=False,indent=2),encoding='utf-8');manifest['projects'].append(snap)
    xlsx(dest/'待报销项目文件表.xlsx',[('项目总览',summary),('发票明细',details),('附件索引',files)])
    (dest/'项目数据.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.make_archive(str(dest),'zip',dest);return dest
