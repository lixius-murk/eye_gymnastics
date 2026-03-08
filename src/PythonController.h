#ifndef PYTHONCONTROLLER_H
#define PYTHONCONTROLLER_H

#include <QObject>
#include <QProcess>

class PythonController : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool running READ running NOTIFY runningChanged)

public:
    explicit PythonController(QObject *parent = nullptr);

    bool running() const { return m_process.state() != QProcess::NotRunning; }

    Q_INVOKABLE void startRenderer(const QString &rendererType,
                                   const QString &blType,
                                   const QString &movement,
                                   int width,
                                   int height);
    Q_INVOKABLE void stopRenderer();

signals:
    void runningChanged();

private:
    QProcess m_process;
    QProcess m_cleanup;
};

#endif // PYTHONCONTROLLER_H
