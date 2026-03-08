#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include "FrameProvider.h"
#include "CameraLogic.h"
#include "PythonController.h"

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QQmlApplicationEngine engine;

    FrameProvider *provider = new FrameProvider();
    engine.addImageProvider("frameprovider", provider);

    CameraLogic camera;
    PythonController python;

    engine.rootContext()->setContextProperty("cameraLogic", &camera);
    engine.rootContext()->setContextProperty("pythonCtrl",  &python);

    engine.load(QUrl(QStringLiteral("qrc:/qt/qml/Main/main.qml")));
    if (engine.rootObjects().isEmpty()) return -1;

    return app.exec();
}
