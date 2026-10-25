"""Resolution-independent outline icons, rendered by Qt without asset downloads."""

from PySide6 import QtCore, QtGui, QtSvg

_PATHS = {
    "home": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "library": '<rect x="3" y="4" width="5" height="16" rx="1"/><path d="M11 4v16M15 5l4-1 3 15-4 1zM4 8h3"/>',
    "chart": '<path d="M4 3v17h17M8 16v-5M13 16V6M18 16V9"/>',
    "star": '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9z"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18M7 14h3M14 14h3M7 17h3"/>',
    "settings": '<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3"/><circle cx="15" cy="17" r="3"/>',
    "import": '<path d="M12 3v12m-4-4 4 4 4-4M4 15v5h16v-5"/>',
    "export": '<path d="M12 15V3m-4 4 4-4 4 4M4 15v5h16v-5"/>',
    "moon": '<path d="M20 14A9 9 0 0 1 10 3a9 9 0 1 0 10 11z"/>',
    "refresh": '<path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-1l2 3M4 15l2 3a7 7 0 0 0 12-1"/>',
    "log": '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/>',
}


def icon(name: str, color: str = "#667B72") -> QtGui.QIcon:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
           f'fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" '
           f'stroke-linejoin="round">{_PATHS[name]}</svg>')
    renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode()))
    pixmap = QtGui.QPixmap(48, 48)
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QtGui.QIcon(pixmap)
