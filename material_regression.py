from pathlib import Path
from types import SimpleNamespace
from tkinter import ttk,messagebox
import hashlib,shutil
import domain as D
import legacy

def run_material_checks(ui,root,inv,check,pdf):
    ui.flush_editor();p=D.project('拖放与批量操作','物资采购');entry=D.add_entry(p,'采购材料');other=D.add_entry(p,'另一个条目');entry['invoices']=[inv('300'),inv('200'),inv('100')];ui.projects=[p];ui.index=0;ui.entry_id=entry['id'];ui.bind_project();ui.show_entry_workspace();ui.update()
    check(str(ui.tree.cget('selectmode'))=='extended' and str(ui.photo_tree.cget('selectmode'))=='extended' and str(ui.attachment_tree.cget('selectmode'))=='extended','发票、配图和附件列表均支持Ctrl/Shift多选')
    ui.tree.select_all();check(len(ui.tree.selection())==3,'发票列表可全选');ui.tree.clear_selected();check(not ui.tree.selection(),'发票列表可取消全选')
    ui.tree.selection_set('0');ui.tree.invert_selected();check(ui.tree.selection()==('1','2'),'发票反选只选择原先未选的发票');ui.tree.invert_selected();check(ui.tree.selection()==('0',),'再次反选恢复原选择')
    ui.tree.selection_set(('0','2'));ui.refresh();check(ui.tree.selection()==('0','2'),'刷新后保留多张发票选择')
    middle_supplier=entry['invoices'][1]['seller'];review=ui.edit();review.invoice_fields['seller'].set('批量核对第一张');review.save_review(True);check(ui.selected()==2 and ui.review_window is not review,'批量核对只前往所选下一张，跳过未选发票');ui.review_window.invoice_fields['seller'].set('批量核对第三张');ui.review_window.save_review();check(entry['invoices'][0]['seller']=='批量核对第一张' and entry['invoices'][2]['seller']=='批量核对第三张' and entry['invoices'][1]['seller']==middle_supplier,'批量核对保存正确的两张发票，未选发票保持原内容')
    original_digest=hashlib.sha256(pdf.read_bytes()).hexdigest();original_ask=messagebox.askyesno;messagebox.askyesno=lambda *args,**kwargs:True
    try:
        ui.tree.selection_set(('0','2'));ui.remove();check(len(entry['invoices'])==1 and entry['invoices'][0]['seller']==middle_supplier,'批量移除发票按倒序处理，不误移除中间未选项')
        entry['invoices']=[inv('300'),inv('200')];ui.bind_project();ui.tabs.select(1);ui.update();ui.photo_invoice_choice.current(1)
        folder=root/'图片 文件夹';(folder/'子目录').mkdir(parents=True);photo_a=folder/'图片 甲.png';photo_b=folder/'子目录'/'图片乙.png';legacy.Image.new('RGB',(80,50),'#217346').save(photo_a);legacy.Image.new('RGB',(80,50),'#444444').save(photo_b);shutil.copy2(photo_a,folder/'同图不同名.png');(folder/'说明.txt').write_text('不是图片',encoding='utf-8')
        def drop_data(paths):return ui.tk.call('format','%s',ui.tk.call('list',*[str(p) for p in paths]))
        ui.on_drop(SimpleNamespace(data=drop_data([folder])));check(len(entry['invoices'][1]['photos'])==2 and not entry['invoices'][0]['photos'] and len(ui.invoices)==2,'图片页拖入整个中文文件夹，递归导入到选定发票且不误作为发票')
        ui.on_drop(SimpleNamespace(data=drop_data([photo_a,photo_b])));check(len(entry['invoices'][1]['photos'])==2,'重复图片按内容去重，不因文件名或拖入次数重复配图')
        ui.photo_invoice_choice.current(0);ui.on_drop(SimpleNamespace(data=drop_data([photo_a])));check(len(entry['invoices'][0]['photos'])==1,'图片页支持拖入单张图片并明确归属对应发票')
        ui.on_drop(SimpleNamespace(data=drop_data([folder/'说明.txt'])));check('失败' in ui.status.get() and len(ui.invoices)==2,'图片区拒绝非图片文件，不转为发票或留下图片占位')
        ui.photo_tree.select_all();check(len(ui.photo_tree.selection())==3,'配图列表跨对应发票全选');ui.photo_tree.invert_selected();check(not ui.photo_tree.selection(),'配图全选后反选变为全不选');ui.photo_tree.clear_selected();check(not ui.photo_tree.selection(),'配图列表可取消全选');ui.photo_tree.select_all();ui.remove_photo();check(all(not i['photos'] for i in entry['invoices']) and photo_a.exists() and photo_b.exists(),'批量移除多张发票的图片关联，不删除源图片')
        ui.tabs.select(2);ui.update();ui.attachment_choice.current(0);note=root/'采购申请 说明.txt';note.write_text('模拟附件内容',encoding='utf-8');ui.on_drop(SimpleNamespace(data=drop_data([pdf,note])));check(len(entry['attachments']['采购申请或审批'])==2 and len(ui.invoices)==2,'附件页支持同时拖入多个文件，进入所选材料类别而不是发票列表')
        ui.update();target=next(row for row,slot in ui._attachment_targets.items() if slot==('attachments','采购入库材料'));box=ui.attachment_tree.bbox(target);check(bool(box),'待补充附件类别有可拖入的可见行')
        ui.on_drop(SimpleNamespace(data=drop_data([pdf]),widget=ui.attachment_tree,y=box[1]+box[3]//2));check(len(entry['attachments']['采购入库材料'])==1,'拖到具体附件行时使用该行类别，不沿用其他下拉类别')
        ui.attachment_tree.select_all();check(len(ui.attachment_tree.selection())==3,'附件全选只选择真实文件，不选择待补充占位行');ui.attachment_tree.invert_selected();check(not ui.attachment_tree.selection(),'附件反选不误选待补充占位行');ui.attachment_tree.invert_selected();ui.remove_entry_attachment();check(not any(entry['attachments'].values()) and note.exists() and pdf.exists(),'附件可跨类别批量移除关联，原文件保留')
        ui.tabs.select(1);ui.update();check(bool(ui.photo_tree.dnd_bind('<<Drop>>')) and bool(ui.attachment_tree.dnd_bind('<<Drop>>')),'图片及附件列表已注册原生拖放事件')
        travel=D.project('差旅拒绝配图','差旅报销');travel_entry=D.add_entry(travel,'交通');travel_entry['invoices']=[inv('8000')];ui.projects=[travel];ui.index=0;ui.entry_id=travel_entry['id'];ui.bind_project();ui.show_entry_workspace();ui.tabs.select(1);ui.on_drop(SimpleNamespace(data=drop_data([photo_a])));check(not travel_entry['invoices'][0]['photos'] and '无需配图' in ui.status.get(),'差旅图片拖入继续遵守无需配图规则')
        ui.projects=[p];ui.index=0;ui.entry_id=entry['id'];ui.bind_project();ui.show_overview();ui.update();row=entry['id']+':0';button=ui._upload_buttons[(row,'invoice')];check(isinstance(button,ttk.Button) and str(button.cget('style'))=='Upload.TButton' and button.winfo_ismapped(),'总览上传入口是可见的真实圆角矩形按钮')
        check(button.winfo_reqheight()<=button.winfo_height(),'圆角上传按钮保留足够文字高度，不发生上下裁切')
        calls=[];old_add=ui.add;ui.add=lambda:calls.append(ui.entry_id)
        try:button.invoke()
        finally:ui.add=old_add
        check(calls==[entry['id']] and ui.view_mode=='project','圆角上传按钮调用正确条目的导入动作并保留总览')
        check(str(ui._upload_buttons[(other['id']+':0','photos')].cget('state'))=='disabled','未导入发票的条目不能通过上传按钮误配图片')
        ui.material_drop(SimpleNamespace(data=drop_data([photo_a])),'overview',row,'photos');check(len(entry['invoices'][0]['photos'])==1,'表格圆角配图按钮也支持拖入并关联该行发票')
        check(all(table.bind('<Button-3>') for table in (ui.tree,ui.photo_tree,ui.attachment_tree,ui.overview_table)),'三类材料列表和总览均提供右键操作菜单')
        ui.tree.selection_set(('0','1'));menu=ui.material_context_menu(ui.tree,'invoices','0');check(ui.tree.selection()==('0','1'),'右键点击已选发票时保留多选结果')
        selection=menu.nametowidget(menu.entrycget(menu.index('end'),'menu'));selection.invoke(1);check(not ui.tree.selection(),'右键选择子菜单的反选可实际执行');selection.invoke(0);check(len(ui.tree.selection())==2,'右键选择子菜单的全选可实际执行')
        ui.tree.selection_set('0');ui.material_context_menu(ui.tree,'invoices','1');check(ui.tree.selection()==('1',),'右键点击未选发票时将目标切到该发票')
        target=next(key for key,value in ui._attachment_targets.items() if value==('attachments','采购入库材料'));ui.material_context_menu(ui.attachment_tree,'attachments',target);check(ui._slots[ui.attachment_choice.current()][1]=='采购入库材料','附件右键菜单命中正确的材料类别')
        calls=[];old_add=ui.add;ui.add=lambda:calls.append(ui.entry_id)
        try:
            menu=ui.overview_context_menu(row);uploads=menu.nametowidget(menu.entrycget(menu.index('end'),'menu'));uploads.invoke(0)
        finally:ui.add=old_add
        check(calls==[entry['id']],'总览右键上传子菜单调用正确条目的导入入口')
        check(bool(ui._upload_buttons[(row,'invoice')].bind('<Button-3>')),'圆角上传按钮表面也能右键打开菜单')
        for n in range(30):D.add_entry(p,'滚动条目 '+str(n))
        ui.refresh();ui.show_overview();ui.update();last=other['id']+':0';ui.overview_table.see(last);ui.update();check(all(ui.overview_table.exists(key[0]) and ui.overview_table.bbox(key[0],key[1]) for key in ui._upload_buttons),'表格滚动后圆角按钮跟随可见行，不遗留在旧行位置')
        routed=[];old_import=ui.import_paths;ui.import_paths=lambda paths:routed.extend(paths)
        try:ui.on_drop(SimpleNamespace(data=drop_data([root/'继续编辑.reimbatch'])))
        finally:ui.import_paths=old_import
        check(routed==[str(root/'继续编辑.reimbatch')],'新增图片附件拖放后，批次文件拖入恢复编辑入口继续保留')
        check(hashlib.sha256(pdf.read_bytes()).hexdigest()==original_digest,'所有批量操作和拖放均保持原始发票字节不变')
    finally:messagebox.askyesno=original_ask
