#include <QApplication>
#include "MainWindow.h"

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

    QApplication::setApplicationName("GestureControl");
    QApplication::setOrganizationName("MyOrg");

    MainWindow w;
    w.show();

    return app.exec();
}
