from django import forms
class UploadForm(forms.Form):
    file = forms.FileField()
class ProcessForm(forms.Form):
    keep_columns = forms.CharField(required=False, widget=forms.TextInput(attrs={"placeholder":"record_id,date,description,address,contractor_owner,valuation,fees"}))
class MappingForm(forms.Form):
    json_text = forms.CharField(widget=forms.Textarea)
class RulesForm(forms.Form):
    json_text = forms.CharField(widget=forms.Textarea)