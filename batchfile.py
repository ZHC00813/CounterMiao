import json,zipfile,hashlib,uuid,tempfile,shutil,os,io
from pathlib import Path
from copy import deepcopy
import domain as D

EXT='.reimbatch'
MAGIC=b'REIMBATCH_AESGCM_1\n'
def encrypt_bytes(raw,password):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    salt=os.urandom(16);nonce=os.urandom(12);key=Scrypt(salt=salt,length=32,n=32768,r=8,p=1).derive(password.encode('utf-8'))
    return MAGIC+salt+nonce+AESGCM(key).encrypt(nonce,raw,MAGIC)
def decrypt_bytes(raw,password):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from cryptography.exceptions import InvalidTag
    if not password:raise ValueError('此批次已加密，请输入密码')
    offset=len(MAGIC);salt=raw[offset:offset+16];nonce=raw[offset+16:offset+28]
    try:
        key=Scrypt(salt=salt,length=32,n=32768,r=8,p=1).derive(password.encode('utf-8'));return AESGCM(key).decrypt(nonce,raw[offset+28:],MAGIC)
    except (InvalidTag,ValueError):raise ValueError('密码不正确，或批次文件已损坏') from None
def is_encrypted(path):
    with open(path,'rb') as f:return f.read(len(MAGIC))==MAGIC
def save_batch(path,batch,projects,deleted=None,password=None,history=None):
    path=Path(path);snapshot=deepcopy(dict(version=3,batch=batch,projects=projects,deleted_records=deleted or [],history=history or []));missing=[]
    with tempfile.TemporaryDirectory(prefix='.batch_',dir=path.parent) as tmp:
        root=Path(tmp);assets=root/'资料'
        visited=set()
        def copy(value):
            if not value:return ''
            if not D.readable(value):missing.append(value);return ''
            target=D.store_file(value,assets);return Path(target).relative_to(root).as_posix()
        def walk(obj):
            if isinstance(obj,(dict,list)):
                if id(obj) in visited:return
                visited.add(id(obj))
            if isinstance(obj,dict):
                for key,value in list(obj.items()):
                    if key=='source' and isinstance(value,str):obj[key]=copy(value)
                    elif key=='photos' and isinstance(value,list):obj[key]=[v for v in map(copy,value) if v]
                    elif key in ['attachments','signed'] and isinstance(value,dict):
                        for label,paths in value.items():value[label]=[v for v in map(copy,paths) if v]
                    else:walk(value)
            elif isinstance(obj,list):
                for v in obj:walk(v)
        walk(snapshot);snapshot['missing_files']=list(dict.fromkeys(missing));(root/'项目数据.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf-8')
        temp=path.with_name(path.name+'.tmp')
        with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
            for source in root.rglob('*'):
                if source.is_file():z.write(source,source.relative_to(root).as_posix())
        with zipfile.ZipFile(temp) as z:
            if z.testzip() is not None:raise ValueError('批次文件完整性检查失败')
        if password:temp.write_bytes(encrypt_bytes(temp.read_bytes(),password))
        os.replace(temp,path)
    return snapshot['missing_files']
def open_batch(path,data_dir,password=None):
    path=Path(path);root=Path(data_dir)/'已打开批次'/uuid.uuid4().hex;root.mkdir(parents=True)
    content=path.read_bytes()
    if content.startswith(MAGIC):content=decrypt_bytes(content,password)
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        if '项目数据.json' not in z.namelist():raise ValueError('不是有效的报销批次文件')
        if len(z.infolist())>30000 or sum(i.file_size for i in z.infolist())>8*1024**3:raise ValueError('批次过大，请拆分后打开')
        for info in z.infolist():
            rel=Path(info.filename)
            if rel.is_absolute() or '..' in rel.parts or ':' in info.filename or '\\' in info.filename:raise ValueError('批次包含不安全的文件路径')
            target=(root/rel).resolve()
            if not target.is_relative_to(root.resolve()):raise ValueError('批次路径越界')
        z.extractall(root)
    return root/'项目数据.json'
