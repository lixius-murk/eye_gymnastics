#include "PythonController.h"
#include <QDir>
#include <QFile>
#include <QCoreApplication>
#include <QGuiApplication>
#include <QScreen>
#include <QDebug>
#include <QString>


PythonController::PythonController(QObject *parent) : QObject(parent)
{
    m_process.setProcessChannelMode(QProcess::MergedChannels);
    connect(&m_process, &QProcess::readyReadStandardOutput, [this](){
        //qDebug() << "Python:" << m_process.readAllStandardOutput();
    });
    connect(&m_process, QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished),
            [this](int code, QProcess::ExitStatus){
                qDebug() << "Python exited, code:" << code;
                emit runningChanged();
            });
    connect(&m_process, &QProcess::started, [this](){
        qDebug() << "Python started, PID:" << m_process.processId();
        emit runningChanged();
    });
}

void PythonController::startRenderer(const QString &rendererType,
                                     const QString &blType,
                                     const QString &movement,
                                     int width,
                                     int height)
{
    if (m_process.state() != QProcess::NotRunning) return;

    QString appDir = QCoreApplication::applicationDirPath();
    QDir dir(appDir);
    while (!dir.exists("python_renderer") && !dir.isRoot())
        dir.cdUp();

    QString projectRoot = dir.absolutePath();
    QString workDir = projectRoot + "/python_renderer";
    #ifdef Q_OS_WIN
        QString python      = workDir + "/.venv/Scripts/python.exe";
        QString cleanScript = projectRoot + "/clean.bat";
        QProcess::execute("cmd", {"/c", cleanScript});
        QString venvBin = workDir + "/.venv/Scripts";
    #else
        QString python      = workDir + "/.venv/bin/python3";
        QString cleanScript = projectRoot + "/clean.sh";
        QProcess::execute("bash", {cleanScript});
        QString venvBin = workDir + "/.venv/bin";
    #endif

    qDebug() << "Project root:" << projectRoot;

    QString script = workDir + "/renderer.py";

    qDebug() << "Project root:" << projectRoot;

    if (!QFile::exists(python)) python = "python3";
    if (!QFile::exists(script)) { qWarning() << "Script not found:" << script; return; }

    QScreen *screen = QGuiApplication::primaryScreen();
    QString w = QString::number(width);
    QString h = QString::number(height);
    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    env.insert("VIRTUAL_ENV", workDir + "/.venv");
    env.insert("PATH", workDir + "/.venv/bin:" + env.value("PATH"));
    env.insert("PYTHONPATH", workDir);

    m_process.setWorkingDirectory(workDir);
    m_process.setProcessEnvironment(env);
    m_process.start(python, {script, rendererType, blType, movement, w, h});
}

void PythonController::stopRenderer()
{
    if (m_process.state() == QProcess::NotRunning) return;
    m_process.terminate();
    if (!m_process.waitForFinished(3000))
        m_process.kill();
    emit runningChanged();
}
