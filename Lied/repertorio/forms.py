from django import forms
from .models import PiezaMusical
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _

class PiezaMusicalForm(forms.ModelForm):
    fecha_composicion = forms.CharField(
        required=False,
        label=_("Fecha de composición"),
        widget=forms.TextInput(attrs={'placeholder': 'Ej: 1788'})
    )
    derechos = forms.CharField(
        required=False,
        label=_("Derechos de autor"),
        initial='Dominio público',
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Dominio público'})
    )
    
    error_messages = {
        'musicxml_invalid': _('Solo archivos MusicXML (.musicxml, .xml)'),
        'file_size': _('El archivo excede 10MB')
    }

    class Meta:
        model = PiezaMusical
        fields = ['fecha_composicion', 'derechos', 'partitura_musicxml']
        widgets = {
            'partitura_musicxml': forms.FileInput(attrs={
                'class': 'form-control-file',
                'accept': '.musicxml,.xml'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['partitura_musicxml'].required = True
        self.fields['partitura_musicxml'].validators.append(
            FileExtensionValidator(
                allowed_extensions=['musicxml', 'xml'],
                message=self.error_messages['musicxml_invalid']
            )
        )

    def clean_partitura_musicxml(self):
        archivo = self.cleaned_data.get('partitura_musicxml')
        if archivo and archivo.size > 10 * 1024 * 1024:
            raise forms.ValidationError(
                self.error_messages['file_size'],
                code='file_too_big'
            )
        return archivo