from myqt.MyQtCommon import QtDialogAutoClose


class QtPopUp(QtDialogAutoClose):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
