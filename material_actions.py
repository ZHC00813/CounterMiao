import os,hashlib
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
import domain as D
import legacy

IMAGE_TYPES={'.png','.jpg','.jpeg','.bmp','.tif','.tiff','.webp'}

def material_files(inputs,images=False):
    files=[];seen=set();skipped=[]
    def add(path):
        try:
            path=Path(path);resolved=str(path.resolve())
            if resolved.casefold() in seen:return
            seen.add(resolved.casefold())
            if not D.readable(resolved) or (images and path.suffix.lower() not in IMAGE_TYPES):skipped.append(str(path));return
            if images:
                from PIL import Image
                with Image.open(path) as picture:picture.verify()
            files.append(resolved)
        except Exception:skipped.append(str(path))
    for value in inputs:
        path=Path(value)
        if path.is_dir():
            for folder,dirs,names in os.walk(path,followlinks=False,onerror=lambda error:skipped.append(str(error))):
                dirs[:]=sorted(d for d in dirs if not (Path(folder)/d).is_symlink())
                for name in sorted(names):add(Path(folder)/name)
        else:add(path)
    return files,skipped

from context_actions import ContextActionsMixin

class MaterialActionsMixin(ContextActionsMixin):
    def selection_controls(self,parent,table,valid=None):
        bar=ttk.Frame(parent);label=tk.StringVar()
        def rows():return list(valid()) if valid else list(table.get_children())
        def select_all(event=None):table.selection_set(rows());update();return 'break'
        def clear(event=None):table.selection_remove(table.selection());update();return 'break'
        def invert(event=None):
            current=set(table.selection());table.selection_set([row for row in rows() if row not in current]);update();return 'break'
        def update(event=None):
            allowed=set(rows());count=len(allowed.intersection(table.selection()));label.set(f'{count} / {len(allowed)} selected' if self.language=='en' else f'已选 {count} / 共 {len(allowed)} 项')
        ttk.Button(bar,text='全选',command=select_all).pack(side='left');ttk.Button(bar,text='反选',command=invert).pack(side='left',padx=(6,0));ttk.Button(bar,text='取消全选',command=clear).pack(side='left',padx=6);ttk.Label(bar,textvariable=label,style='Muted.TLabel').pack(side='left',padx=6);ttk.Label(bar,text='可拖入 · Ctrl / Shift 多选',style='Muted.TLabel').pack(side='right')
        table.bind('<Control-a>',select_all);table.bind('<Control-A>',select_all);table.bind('<Control-i>',invert);table.bind('<Control-I>',invert);table.bind('<<TreeviewSelect>>',update,add='+');table._update_selection_count=update;table.select_all=select_all;table.invert_selected=invert;table.clear_selected=clear;update();return bar
    def selected_invoice_indices(self):return sorted(int(row) for row in self.tree.selection() if row.isdigit() and int(row)<len(self.invoices))
    def remove(self):
        indices=self.selected_invoice_indices()
        if not indices:return
        if not messagebox.askyesno('移除所选发票',f'从当前条目移除 {len(indices)} 张发票及其配图关联？原文件不会删除。',parent=self):return
        self.tree.selection_remove(self.tree.selection())
        for index in reversed(indices):self.invoices.pop(index)
        self.refresh();self.status.set(f'已移除 {len(indices)} 张发票的关联，原文件保留。')
    def next_review_index(self,current):
        queue=getattr(self,'_review_indices',[])
        return next((n for n in queue if n>current and n<len(self.invoices)),None)
    def photo_target_index(self):
        if self.tabs.index(self.tabs.select())==0:
            indices=self.selected_invoice_indices()
            if len(indices)==1:return indices[0]
            if len(indices)>1:raise ValueError('请先选择一张对应发票，再批量添加它的图片；不会把图片自动分配给多张发票。')
            return None
        index=self.photo_invoice_choice.current();return index if index>=0 else None
    def add_photo_folder(self):
        folder=filedialog.askdirectory(title='选择图片文件夹')
        if folder:
            try:self.import_material_paths('photos',[folder])
            except Exception as error:messagebox.showerror('图片添加失败',str(error),parent=self)
    def add_attachment_folder(self):
        folder=filedialog.askdirectory(title='选择附件文件夹')
        if folder:
            try:self.import_material_paths('attachments',[folder])
            except Exception as error:messagebox.showerror('附件添加失败',str(error),parent=self)
    def import_material_paths(self,kind,inputs,index=None,slot=None):
        if self.importing:raise ValueError('请等待发票导入完成，再添加图片或附件。')
        if not self.current_entry():raise ValueError('请先选择一个报销条目。')
        if kind=='photos':
            if self.kind=='差旅报销':raise ValueError('差旅报销无需配图。')
            if index is None:index=self.photo_target_index()
            if index is None or not 0<=index<len(self.invoices):raise ValueError('请先选择对应发票，再添加图片。')
        elif slot is None:
            selected=self.attachment_choice.current()
            if not 0<=selected<len(self._slots):raise ValueError('请先选择附件类别。')
            slot=self._slots[selected][:2]
        paths,skipped=material_files(inputs,images=kind=='photos')
        if not paths:raise ValueError('没有可导入的'+('有效图片' if kind=='photos' else '非空文件')+'。')
        if kind=='photos':before=len(self.invoices[index].get('photos',[]));self.attach_photo_paths(index,paths);added=len(self.invoices[index].get('photos',[]))-before
        else:
            collection,key=slot;e=self.current_entry();bucket=e['attachments'] if collection=='attachments' else self.current()['types'][e['kind']]['signed'];before=len(bucket.get(key,[]));self.attach_entry_paths(collection,key,paths);added=len(bucket.get(key,[]))-before
        self.status.set(f'已添加 {added} 个文件；跳过重复 {len(paths)-added} 个、不支持或无法读取 {len(skipped)} 个。');return added
    def register_material_drop(self,widget,kind,iid=None,column=None):
        widget.drop_target_register(legacy.DND_FILES);widget.dnd_bind('<<DropEnter>>',lambda event:legacy.COPY)
        widget.dnd_bind('<<Drop>>',lambda event:self.material_drop(event,kind,iid,column))
    def material_drop(self,event,kind,iid=None,column=None):
        try:
            paths=self.tk.splitlist(event.data)
            if kind=='overview':return self.overview_drop(event,iid,column,paths)
            slot=None
            if kind=='attachments':
                row=None
                if hasattr(event,'y_root'):row=self.attachment_tree.identify_row(event.y_root-self.attachment_tree.winfo_rooty())
                elif getattr(event,'widget',None) is self.attachment_tree:row=self.attachment_tree.identify_row(event.y)
                if row in self._attachment_targets:slot=self._attachment_targets[row]
            self.import_material_paths(kind,paths,slot=slot)
        except Exception as error:self.status.set('拖入失败：'+str(error))
        return legacy.COPY
    def on_drop(self,event):
        paths=self.tk.splitlist(event.data)
        if len(paths)==1 and str(paths[0]).lower().endswith('.reimbatch'):
            self.import_paths(paths);return legacy.COPY
        if hasattr(self,'overview_table') and getattr(self,'view_mode','entry')=='project':return self.material_drop(event,'overview')
        if hasattr(self,'tabs') and getattr(self,'view_mode','entry')=='entry':
            tab=self.tabs.index(self.tabs.select())
            if tab in (1,2):return self.material_drop(event,'photos' if tab==1 else 'attachments')
        return super().on_drop(event)
    def open_material_paths(self,paths):
        errors=[]
        for path in dict.fromkeys(paths):
            try:os.startfile(path)
            except Exception:errors.append(Path(path).name)
        if errors:messagebox.showerror('无法打开文件','\n'.join(errors),parent=self)
    def open_photo(self):self.open_material_paths([self._photo_rows[row][2] for row in self.photo_tree.selection() if row in self._photo_rows])
    def remove_photo(self):
        selected=[self._photo_rows[row] for row in self.photo_tree.selection() if row in self._photo_rows]
        if not selected:return
        if not messagebox.askyesno('移除所选图片',f'移除 {len(selected)} 张图片的关联？原文件不会删除。',parent=self):return
        self.photo_tree.selection_remove(self.photo_tree.selection())
        for n,j,path in sorted(selected,key=lambda row:(row[0],row[1]),reverse=True):self.invoices[n]['photos'].pop(j)
        self.refresh()
    def open_entry_attachment(self):self.open_material_paths([self._attachment_rows[row][3] for row in self.attachment_tree.selection() if row in self._attachment_rows])
    def remove_entry_attachment(self):
        selected=[self._attachment_rows[row] for row in self.attachment_tree.selection() if row in self._attachment_rows]
        if not selected:return
        if not messagebox.askyesno('移除所选附件',f'移除 {len(selected)} 个附件的关联？原文件不会删除。',parent=self):return
        self.attachment_tree.selection_remove(self.attachment_tree.selection());e=self.current_entry()
        for kind,key,n,path in sorted(selected,key=lambda row:(row[0],row[1],row[2]),reverse=True):
            bucket=e['attachments'] if kind=='attachments' else self.current()['types'][e['kind']]['signed'];bucket[key].pop(n)
        self.refresh()
    def stored_material_paths(self,paths,folder,existing):
        hashes={hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in existing if D.readable(p)};stored=[]
        for path in paths:
            digest=hashlib.sha256(Path(path).read_bytes()).hexdigest()
            if digest in hashes:continue
            hashes.add(digest);stored.append(D.store_file(path,folder))
        return list(existing)+stored
