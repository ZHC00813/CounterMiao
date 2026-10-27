import tkinter as tk

class ContextActionsMixin:
    def material_context_menu(self,table,kind,row=None):
        table.focus_set()
        valid=set(self._attachment_rows) if kind=='attachments' else set(table.get_children())
        if row in valid and row not in table.selection():table.selection_set(row)
        if kind=='photos' and row in self._photo_rows:self.photo_invoice_choice.current(self._photo_rows[row][0])
        if kind=='attachments' and row in self._attachment_targets:
            slot=self._attachment_targets[row]
            index=next((n for n,option in enumerate(self._slots) if option[:2]==slot),None)
            if index is not None:self.attachment_choice.current(index)
        old=getattr(self,'_file_context_menu',None)
        if old:old.destroy()
        menu=tk.Menu(self,tearoff=False);self._file_context_menu=menu
        selected=[key for key in table.selection() if key in valid];enabled='normal' if selected else 'disabled'
        menu.add_command(label=f'Selected {len(selected)} items' if self.language=='en' else f'已选 {len(selected)} 项',state='disabled')
        imports=tk.Menu(menu,tearoff=False);menu.add_cascade(label='导入材料',menu=imports)
        if kind=='invoices':
            imports.add_command(label='选择发票（可多选）',command=self.add);imports.add_command(label='选择发票文件夹',command=self.add_folder)
            menu.add_command(label='核对所选发票',state=enabled,command=self.edit)
            menu.add_command(label='打开所选原始发票',state=enabled,command=lambda:self.open_material_paths([self.invoices[n]['source'] for n in self.selected_invoice_indices()]))
            remove=self.remove
        elif kind=='photos':
            allowed='normal' if self.invoices and self.kind!='差旅报销' else 'disabled'
            imports.add_command(label='选择图片（可多选）',state=allowed,command=self.add_invoice_photos);imports.add_command(label='选择图片文件夹',state=allowed,command=self.add_photo_folder)
            menu.add_command(label='打开所选图片',state=enabled,command=self.open_photo);remove=self.remove_photo
        else:
            imports.add_command(label='选择附件（可多选）',command=self.add_entry_attachments);imports.add_command(label='选择附件文件夹',command=self.add_attachment_folder)
            categories=tk.Menu(imports,tearoff=False);imports.add_cascade(label='切换附件类别',menu=categories)
            for index,(_,_,label) in enumerate(self._slots):categories.add_command(label=label,command=lambda n=index:self.attachment_choice.current(n))
            menu.add_command(label='打开所选附件',state=enabled,command=self.open_entry_attachment);remove=self.remove_entry_attachment
        menu.add_command(label='移除所选关联',state=enabled,command=remove);menu.add_separator()
        selection=tk.Menu(menu,tearoff=False);selection.add_command(label='全选',accelerator='Ctrl+A',command=table.select_all);selection.add_command(label='反选',accelerator='Ctrl+I',command=table.invert_selected);selection.add_command(label='取消全选',command=table.clear_selected);menu.add_cascade(label='选择操作',menu=selection)
        self.localize_widget(menu);return menu
    def show_material_context(self,event,table,kind):
        menu=self.material_context_menu(table,kind,table.identify_row(event.y))
        try:menu.tk_popup(event.x_root,event.y_root)
        finally:menu.grab_release()
        return 'break'
    def overview_context_menu(self,row=None):
        old=getattr(self,'_overview_context_menu',None)
        if old:old.destroy()
        menu=tk.Menu(self,tearoff=False);self._overview_context_menu=menu;menu.add_command(label='新建报销条目',command=self.overview_new_entry)
        target=self.overview_rows.get(row)
        if target:
            self.overview_table.selection_set(row);entry,index=target
            menu.add_command(label='编辑该报销条目',command=self.overview_open_entry)
            uploads=tk.Menu(menu,tearoff=False);menu.add_cascade(label='上传材料',menu=uploads)
            for column,label in [('invoice','上传发票'),('photos','上传配图'),('attachment','上传附件')]:
                disabled=column=='photos' and (index is None or entry['kind']=='差旅报销')
                uploads.add_command(label=label,state='disabled' if disabled else 'normal',command=lambda col=column:self.overview_upload(row,col))
        self.localize_widget(menu);return menu
    def show_overview_context(self,event,row=None):
        menu=self.overview_context_menu(row or self.overview_table.identify_row(event.y))
        try:menu.tk_popup(event.x_root,event.y_root)
        finally:menu.grab_release()
        return 'break'
