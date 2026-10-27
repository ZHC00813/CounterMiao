import os
import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from pathlib import Path
import domain as D

class TreeMixin:
    def current_entry(self):
        return next((e for e in self.current().get('entries',[]) if e['id']==getattr(self,'entry_id',None)),None)
    def sync_all(self):
        for p in self.projects:D.sync(p)
    def build_navigation(self):
        packed=list(self.pack_slaves());options={w:w.pack_info() for w in packed}
        for w in packed:w.pack_forget()
        self.split=ttk.Panedwindow(self,orient='horizontal');self.split.pack(fill='both',expand=True)
        side=ttk.Frame(self.split,width=260);main=ttk.Frame(self.split);self.split.add(side,weight=0);self.split.add(main,weight=1)
        for w in packed:
            info=options[w];info.pop('in',None);w.pack(in_=main,**info)
            if isinstance(w,ttk.Frame):
                buttons=[b for b in w.winfo_children() if isinstance(b,ttk.Button)]
                if buttons and any(b.cget('text')=='导入发票' for b in buttons):
                    for b in buttons:b.pack_forget()
                    for n,b in enumerate(buttons):b.grid(row=n//5,column=n%5,sticky='ew',padx=2,pady=3)
                    for n in range(5):w.columnconfigure(n,weight=1)
                elif buttons and any(b.cget('text')=='附件 / 签字验收单' for b in buttons):
                    for b in buttons:b.pack_forget()
                    for n,b in enumerate(buttons):b.grid(row=n//3,column=n%3,sticky='ew',padx=3,pady=3)
                    for n in range(3):w.columnconfigure(n,weight=1)
                elif buttons and self.project_choice in w.winfo_children():
                    children=w.winfo_children()
                    for child in children:child.pack_forget()
                    for n,child in enumerate(children):child.grid(row=n//4,column=n%4,sticky='w',padx=3,pady=3)
                elif not buttons and w.winfo_children() and all(isinstance(c,ttk.Label) for c in w.winfo_children()):
                    for child in w.winfo_children():child.pack_forget();child.pack(anchor='w');child.configure(wraplength=800)
            if isinstance(w,ttk.Label):w.configure(wraplength=800)
        side.configure(padding=(10,12));self.nav_side=side
        ttk.Label(side,text='工作目录',font=('Microsoft YaHei UI',12,'bold')).pack(anchor='w',pady=(0,10))
        tools=ttk.Frame(side);tools.pack(fill='x');tools.columnconfigure(0,weight=1)
        ttk.Button(tools,text='新建报销项',style='Primary.TButton',command=self.new_project).grid(row=0,column=0,sticky='ew',pady=(0,6));ttk.Button(tools,text='新建报销条目',command=self.new_entry).grid(row=1,column=0,sticky='ew')
        self.nav_bottom=ttk.Frame(side);self.nav_bottom.pack(side='bottom',fill='x',pady=(8,0));ttk.Separator(self.nav_bottom).pack(fill='x',pady=(0,6))
        more=ttk.Menubutton(self.nav_bottom,text='批次与工具');more.pack(fill='x');self.batch_tools_menu=tk.Menu(more,tearoff=False);more.configure(menu=self.batch_tools_menu)
        for label,cmd in [('新建批次',self.new_batch),('保存批次',self.save),('修改记录',self.view_history),('回收站',self.recycle_bin),('AI / 操作接口',self.ai_panel)]:self.batch_tools_menu.add_command(label=label,command=cmd)
        self.show_hidden=tk.BooleanVar(value=False);ttk.Checkbutton(self.nav_bottom,text='显示隐藏项',variable=self.show_hidden,command=self.rebuild_tree).pack(anchor='w',pady=(6,0))
        treeframe=ttk.Frame(side);treeframe.pack(fill='both',expand=True,pady=(12,0));treeframe.rowconfigure(0,weight=1);treeframe.columnconfigure(0,weight=1)
        self.nav=ttk.Treeview(treeframe,show='tree',selectmode='browse',height=4);self.nav.grid(row=0,column=0,sticky='nsew');ys=ttk.Scrollbar(treeframe,command=self.nav.yview);ys.grid(row=0,column=1,sticky='ns');self.nav.configure(yscrollcommand=ys.set);self.nav.tag_configure('red',foreground='#b43a3a');self.nav.tag_configure('hidden',foreground='#777777')
        self.nodes={};self.nav.bind('<<TreeviewSelect>>',self.tree_select);self.nav.bind('<Double-1>',self.open_node);self.nav.bind('<Button-3>',self.context);self.nav.bind('<ButtonRelease-1>',self.click_entry)
        self.nav_menu=tk.Menu(self,tearoff=False)
        self.split.sashpos(0,240);self.rebuild_tree();self.build_workspace(main);self.split.bind('<Configure>',self.initialize_sidebar,add='+')
    def initialize_sidebar(self,event):
        if event.width<600 or getattr(self,'_nav_sized',False):return
        self._nav_sized=True;self.after_idle(lambda:self.split.sashpos(0,min(280,max(220,int(event.width*.22)))))
    def rebuild_tree(self):
        if not hasattr(self,'nav'):return
        self.rebuilding=True
        from preferences import EN
        english=getattr(self,'language','zh')=='en'
        known=set(self.nodes);opened={iid for iid in self.nodes if self.nav.exists(iid) and self.nav.item(iid,'open')};selected=self.nav.selection()
        self.nav.delete(*self.nav.get_children());self.nodes={}
        def put(parent,iid,text,node,open=False):
            self.nodes[iid]=node;obj=node.get('obj',{});tags=[]
            if obj.get('red'):tags.append('red')
            if obj.get('hidden'):tags.append('hidden')
            self.nav.insert(parent,'end',iid=iid,image=self.node_icon(node['type']),text=('● ' if obj.get('red') else '')+text,open=(iid in opened) if iid in known else open,tags=tags)
        bid='b:'+self.batch['id'];put('',bid,('Batch: ' if english else '批次：')+self.batch['name'],dict(type='batch',obj=self.batch),True)
        for p in self.projects:
            if p.get('placeholder'):continue
            if p.get('hidden') and not self.show_hidden.get():continue
            kind=D.parent_kind(p);pid='p:'+p['id'];put(bid,pid,p['name']+(' · '+kind if kind else ' · 旧版混合类型')+('（隐藏）' if p.get('hidden') else ''),dict(type='project',obj=p,project=p),True)
            for e in p.get('entries',[]):
                if e.get('hidden') and not self.show_hidden.get():continue
                eid='e:'+e['id'];put(pid,eid,e['name']+' · '+(EN.get(e['kind'],e['kind']) if english else e['kind'])+f' ({len(e["invoices"])}'+(' invoices)' if english else '票)'),dict(type='entry',obj=e,project=p),True)
                rows=[]
                for inv in e['invoices']:
                    rows.append(('发票',Path(inv['source']).name,inv.get('source',''),inv))
                    for path in inv.get('photos',[]):rows.append(('配图',Path(path).name,path,inv))
                for label,paths in e.get('attachments',{}).items():
                    for path in paths:rows.append((label,Path(path).name,path,None))
                for b in D.plan(self.projects,p,e['kind'])[0]:
                    if any(i.get('entry_id')==e['id'] for i in b['invoices']):
                        for path in p['types'][e['kind']]['signed'].get(b['id'],[]):rows.append(('签字验收单',b['id']+' · '+Path(path).name,path,None))
                folders={}
                for n,(label,name,path,invoice) in enumerate(rows):
                    if label not in folders:
                        fid=eid+':folder:'+str(len(folders));folders[label]=fid;put(eid,fid,EN.get(label,label) if english else label,dict(type='folder',obj={},project=p,entry=e))
                    iid=eid+':file:'+str(n);put(folders[label],iid,name,dict(type='file',obj={},project=p,entry=e,path=path,invoice=invoice))
        target=selected[0] if selected and getattr(self,'from_tree',False) else ('e:'+self.entry_id if getattr(self,'entry_id',None) else 'p:'+self.current()['id'])
        if self.nav.exists(target):self.last_nav_target=target;self.nav.selection_set(target)
        self.rebuilding=False
    def click_entry(self,event):
        iid=self.nav.identify_row(event.y)
        if iid and self.nodes.get(iid,{}).get('type')=='entry':
            self.nav.selection_set(iid);self.tree_select();self.show_entry_workspace();self.tabs.select(0)
    def tree_select(self,event=None):
        if self.rebuilding or self.importing:return
        ids=self.nav.selection()
        if not ids:return
        if not self.flush_editor():return
        if self.nav.exists(ids[0]) and self.nav.selection()!=ids:self.nav.selection_set(ids[0])
        node=self.nodes.get(ids[0])
        if not node:return
        if node['type']=='project' and node['project'] is self.current() and getattr(self,'last_nav_target',None)==ids[0]:self.show_overview();return
        e=node.get('entry') or (node['obj'] if node['type']=='entry' else None)
        if node.get('project') is self.current() and e and self.entry_id==e['id'] and getattr(self,'_workspace_id',None)==e['id']:return
        self.last_nav_target=ids[0]
        if node['type']=='batch':return
        p=node['project'];self.index=self.projects.index(p)
        e=node.get('entry') or (node['obj'] if node['type']=='entry' else None)
        self.entry_id=e['id'] if e else None
        if e:self.kind=e['kind']
        self.from_tree=True
        try:self.bind_project()
        finally:self.from_tree=False
        if node['type']=='project':self.show_overview()
        elif e:self.show_entry_workspace()
    def open_node(self,event=None):
        s=self.nav.selection()
        if not s:return
        node=self.nodes.get(s[0],{})
        if node.get('type')=='entry':self.focus_entry_editor();return
        if node.get('type')=='file':
            try:os.startfile(node['path'])
            except Exception as e:messagebox.showerror('文件无法打开',str(e))
    def new_entry(self,on_created=None):
        if self.importing:return
        if not self.flush_editor():return
        if not D.parent_kind(self.current()):
            messagebox.showinfo('请先确定报销项类型','请先新建报销项，选择类型并填写名称。旧版混合类型数据不会被更改。');self.new_project(on_created=lambda:self.new_entry(on_created));return
        name=simpledialog.askstring('新建报销条目','填写报销条目名称（例如：传感器采购、深圳调研交通）：',parent=self)
        if not name or not name.strip():return
        e=D.add_entry(self.current(),name);self.entry_id=e['id'];self.kind=e['kind'];self.bind_project();self.focus_entry_editor()
        if on_created:self.after(0,on_created)
    def focus_entry_editor(self):
        self.show_entry_workspace();self.tabs.select(0);self.entry_name_input.focus_set();self.entry_name_input.selection_range(0,'end')
    def import_paths(self,inputs):
        if len(inputs)==1 and str(inputs[0]).lower().endswith('.reimbatch'):self.load_path(inputs[0]);return
        if not self.current_entry():messagebox.showinfo('请先新建报销条目','请在左侧新建并填写报销条目名称，再导入或拖入发票。');self.new_entry(on_created=lambda:self.import_paths(inputs));return
        return super().import_paths(inputs)
    def rename_entry(self,e):
        name=simpledialog.askstring('修改报销条目名称','报销条目名称：',initialvalue=e['name'],parent=self)
        if name and name.strip():e['name']=name.strip();self.refresh()
    def context(self,event):
        iid=self.nav.identify_row(event.y)
        if not iid:return
        self.nav.selection_set(iid);self.tree_select();node=self.nodes[iid];self.nav_menu.delete(0,'end')
        self.nav_menu.add_command(label='显示父子关系（箭头）',command=lambda:self.relationships(iid))
        if node['type']=='batch':
            self.nav_menu.add_command(label='新建报销项',command=self.new_project);self.nav_menu.add_command(label='保存整个批次',command=self.save);self.nav_menu.add_command(label='重命名批次',command=self.rename_batch)
        if node['type']=='file':self.nav_menu.add_command(label='打开文件',command=self.open_node)
        if node['type'] in ['project','entry']:
            self.nav_menu.add_command(label='新建报销条目',command=self.new_entry)
            if node['type']=='entry':self.nav_menu.add_command(label='编辑报销条目 / 添加材料',command=self.focus_entry_editor);self.nav_menu.add_command(label='修改报销条目名称',command=lambda:self.rename_entry(node['obj']))
            self.nav_menu.add_command(label='取消标红' if node['obj'].get('red') else '标红',command=lambda:self.toggle(node,'red'))
            self.nav_menu.add_command(label='取消隐藏' if node['obj'].get('hidden') else '隐藏',command=lambda:self.toggle(node,'hidden'))
            self.nav_menu.add_separator();self.nav_menu.add_command(label='删除'+('报销项' if node['type']=='project' else '报销条目'),command=lambda:self.delete_node(node))
        self.localize_widget(self.nav_menu);self.nav_menu.tk_popup(event.x_root,event.y_root)
    def rename_batch(self):
        name=simpledialog.askstring('批次名称','批次名称：',initialvalue=self.batch['name'],parent=self)
        if name and name.strip():self.batch['name']=name.strip();self.bind_project()
    def toggle(self,node,key):node['obj'][key]=not node['obj'].get(key,False);self.persist();self.rebuild_tree()
    def delete_node(self,node):
        if self.importing:return
        if not messagebox.askyesno('删除确认','删除“'+node['obj']['name']+'”及其关联记录？原发票和已归档材料不会删除。'):return
        node['obj']['_record_type']=node['type']
        if node['type']=='entry':node['obj']['_parent_id']=node['project']['id']
        self.deleted_records=getattr(self,'deleted_records',[])+[node['obj']]
        if node['type']=='project':
            self.projects.remove(node['obj']);self.index=0
            if not self.projects:self.projects=[D.project('新报销项目')]
        else:
            p=node['project'];p['entries'].remove(node['obj'])
            if not p['entries']:
                for t in p['types'].values():t['invoices']=[]
        self.entry_id=None;self.bind_project()
    def recycle_bin(self):
        win=tk.Toplevel(self);win.title('可恢复的已删除记录');win.geometry('650x440');listing=tk.Listbox(win);listing.pack(fill='both',expand=True,padx=15,pady=15)
        records=list(getattr(self,'deleted_records',[]))
        for r in records:listing.insert('end',r.get('name','')+' · '+r.get('_record_type','project'))
        def restore():
            s=listing.curselection()
            if not s:return
            try:self.execute_action(dict(op='restore',record_id=records[s[0]]['id']));win.destroy()
            except Exception as e:messagebox.showerror('无法恢复',str(e))
        ttk.Button(win,text='恢复所选记录',command=restore).pack(pady=10)
    def relationships(self,iid):
        if not self.nav.exists(iid):return
        parent=self.nav.parent(iid);children=self.nav.get_children(iid)
        win=tk.Toplevel(self);win.title('父子关系 · '+self.nav.item(iid,'text'));win.geometry('840x540')
        canvas=tk.Canvas(win,bg='white',highlightthickness=0,scrollregion=(0,0,840,max(540,len(children)*90+220)));canvas.pack(fill='both',expand=True)
        scroll=ttk.Scrollbar(win,orient='vertical',command=canvas.yview);scroll.pack(side='right',fill='y');canvas.configure(yscrollcommand=scroll.set)
        def box(x,y,text,color='#217346'):
            canvas.create_rectangle(x-120,y-26,x+120,y+26,outline=color,width=2);canvas.create_text(x,y,text=text,width=225,fill=color)
        label=self.nav.item(iid,'text');box(420,65,self.nav.item(parent,'text') if parent else '项目库');box(420,170,label,'#bb301b');canvas.create_line(420,91,420,143,arrow='last',width=2,fill='#217346')
        if not children:canvas.create_text(420,245,text='此节点没有子节点',fill='#666666')
        for n,child in enumerate(children):
            y=270+n*85;box(550,y,self.nav.item(child,'text'));canvas.create_line(420,196,300,y,430,y,arrow='last',width=2,fill='#217346')
