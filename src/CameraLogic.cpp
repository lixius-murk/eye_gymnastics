#include "CameraLogic.h"
#include <QMediaDevices>
#include <QDebug>
#include <QDir>
#include <QDateTime>
#include <QUrl>
#include <QCoreApplication>
#include <QTimer>
#include <QMediaFormat>


CameraLogic::CameraLogic(QObject *parent) : QObject(parent) {}
CameraLogic::~CameraLogic() { stop(); }

void CameraLogic::toggle() { m_active ? stop() : start(); }

void CameraLogic::start()
{
    if (m_active) return;

    auto devices = QMediaDevices::videoInputs();
    if (devices.isEmpty()) { qWarning() << "No camera found"; return; }

    QDir dir(QCoreApplication::applicationDirPath());
    while (!dir.exists("data") && !dir.isRoot()) dir.cdUp();
    dir.mkpath("data/videos");
    QString timestamp = QDateTime::currentDateTime().toString("yyyyMMdd_HHmmss");
    QString outputPath = dir.absolutePath() + "/data/videos/" + timestamp + ".mp4";

    m_camera   = new QCamera(devices[0], this);
    m_sink     = new QVideoSink(this);
    m_session  = new QMediaCaptureSession(this);
    m_recorder = new QMediaRecorder(this);
    //don't change order
    m_session->setCamera(m_camera);
    m_session->setVideoSink(m_sink);
    m_session->setRecorder(m_recorder);

    QMediaFormat format;
    format.setFileFormat(QMediaFormat::MPEG4);
    format.setVideoCodec(QMediaFormat::VideoCodec::H264);
    m_recorder->setMediaFormat(format);
    m_recorder->setOutputLocation(QUrl::fromLocalFile(outputPath));
    m_recorder->setQuality(QMediaRecorder::HighQuality);
    m_recorder->setVideoResolution(1280, 720);

    connect(m_recorder, &QMediaRecorder::errorOccurred,
            [](QMediaRecorder::Error error, const QString &errorString){
                qDebug() << "Recorder error:" << error << errorString;
            });

    connect(m_recorder, &QMediaRecorder::recorderStateChanged,
            [](QMediaRecorder::RecorderState state){
                qDebug() << "Recorder state:" << state;
            });

    connect(m_sink, &QVideoSink::videoFrameChanged, this, &CameraLogic::onFrame);

    m_camera->start();

    QTimer::singleShot(500, this, [this](){
        m_recorder->record();
        qDebug() << "Recording started";
    });

    m_active = true;
    emit activeChanged();
    qDebug() << "Camera started, recording to:" << outputPath;
}
void CameraLogic::stop()
{
    if (!m_active) return;

    if (m_recorder) { m_recorder->stop(); m_recorder->deleteLater(); m_recorder = nullptr; }
    if (m_camera)   { m_camera->stop();   m_camera->deleteLater(); m_camera = nullptr; }
    if (m_sink)     { m_sink->deleteLater(); m_sink = nullptr; }
    if (m_session)  { m_session->deleteLater(); m_session = nullptr; }

    m_active = false;
    emit activeChanged();
    qDebug() << "Camera stopped";
}

void CameraLogic::onFrame(const QVideoFrame &frame)
{
    if (!frame.isValid()) return;
    QImage img = frame.toImage().convertToFormat(QImage::Format_RGB888);
    if (!img.isNull()) emit frameReady(img);
}
