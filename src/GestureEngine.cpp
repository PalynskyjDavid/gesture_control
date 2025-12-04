#include "GestureEngine.h"

#include <QCoreApplication>
#include <QDebug>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QJsonValue>
#include <QStringList>

GestureEngine::GestureEngine(QObject *parent)
    : QObject(parent)
{
    connect(&socket_, &QTcpSocket::connected,
            this, &GestureEngine::onConnected);

    connect(&socket_, &QTcpSocket::disconnected,
            this, &GestureEngine::onDisconnected);

    connect(&socket_, &QTcpSocket::readyRead,
            this, &GestureEngine::onReadyRead);

    connect(&socket_,
            QOverload<QAbstractSocket::SocketError>::of(&QTcpSocket::errorOccurred),
            this, &GestureEngine::onError);
}

void GestureEngine::setEndpoint(const QString &host, quint16 port)
{
    host_ = host;
    port_ = port;
}

void GestureEngine::setConfigFile(const QString &relativePath)
{
    configFile_ = relativePath;
}

void GestureEngine::start()
{
    loadConfigIfAvailable();
    if (socket_.state() != QAbstractSocket::UnconnectedState)
        socket_.abort();
    emit connectionStatusChanged(
        tr("Connecting to %1:%2").arg(host_).arg(port_));
    socket_.connectToHost(host_, port_);
}

void GestureEngine::stop()
{
    if (socket_.state() != QAbstractSocket::UnconnectedState)
    {
        socket_.disconnectFromHost();
        socket_.waitForDisconnected(1000);
    }
    emit connectionStatusChanged(tr("Disconnected"));
}

void GestureEngine::onConnected()
{
    emit connectionStatusChanged(
        tr("Connected to %1:%2").arg(host_).arg(port_));
}

void GestureEngine::onDisconnected()
{
    emit connectionStatusChanged(tr("Disconnected"));
}

void GestureEngine::onError(QAbstractSocket::SocketError)
{
    emit connectionStatusChanged(tr("Connection error: %1")
                                     .arg(socket_.errorString()));
}

void GestureEngine::onReadyRead()
{
    buffer_.append(QString::fromUtf8(socket_.readAll()));

    while (true)
    {
        int idx = buffer_.indexOf('\n');
        if (idx < 0)
            return;

        const QString jsonStr = buffer_.left(idx);
        buffer_.remove(0, idx + 1);
        if (!jsonStr.trimmed().isEmpty())
            processJson(jsonStr);
    }
}

void GestureEngine::processJson(const QString &jsonStr)
{
    QJsonParseError err;
    QJsonDocument doc = QJsonDocument::fromJson(jsonStr.toUtf8(), &err);

    if (err.error != QJsonParseError::NoError)
    {
        qWarning() << "[GestureEngine] JSON parse error:"
                   << err.errorString();
        return;
    }

    if (!doc.isObject())
        return;

    const QJsonObject root = doc.object();
    const QJsonArray handsArr = root["hands"].toArray();

    QVector<HandInfo> hands;
    hands.reserve(handsArr.size());

    for (const QJsonValue &val : handsArr)
    {
        const QJsonObject obj = val.toObject();
        HandInfo h;
        h.handedness = obj.value("handedness").toString();

        // Default to true if the hand is present in the list, as the Python side might omit it.
        h.visible = obj.value("visible").toBool(true);

        // Convert gesture to lowercase to match C++ binding keys (e.g., "FIST" -> "fist").
        h.gesture = obj.value("gesture").toString().toLower();

        h.confidence = float(obj.value("confidence").toDouble(1.0));
        h.pinchDistance = float(obj.value("pinch_distance").toDouble(0.0));
        h.thumbAngle = float(obj.value("thumb_angle").toDouble(0.0));

        // Safely handle the 'curls' array if it's missing.
        if (obj.contains("curls") && obj.value("curls").isArray())
        {
            const QJsonArray curlsArr = obj.value("curls").toArray();
            for (int i = 0; i < 4 && i < curlsArr.size(); ++i)
                h.curls[i] = curlsArr[i].toBool();
        }
        else
        {
            for (int i = 0; i < 4; ++i)
                h.curls[i] = false; // Default to not curled
        }

        const QJsonObject wrist = obj["wrist"].toObject();
        h.wristX = float(wrist.value("x").toDouble());
        h.wristY = float(wrist.value("y").toDouble());
        h.wristZ = float(wrist.value("z").toDouble(0.0)); // Default Z to 0 if missing

        hands.append(h);
    }

    emit handsUpdated(hands);

    QString bestGesture;
    float bestConfidence = 0.0f;
    bool gestureFound = false;

    for (const auto &hand : hands)
    {
        if (!hand.visible)
            continue;
        if (hand.gesture.isEmpty() || hand.gesture == "none" || hand.gesture == "unknown")
            continue;

        if (!gestureFound || hand.confidence > bestConfidence)
        {
            bestGesture = hand.gesture;
            bestConfidence = hand.confidence;
            gestureFound = true;
        }
    }

    if (!gestureFound)
    {
        lastGestureEmitted_.clear();
        return;
    }

    if (bestGesture != lastGestureEmitted_)
    {
        lastGestureEmitted_ = bestGesture;
        emit gestureDetected(bestGesture);
    }
}

void GestureEngine::loadConfigIfAvailable()
{
    const QString path = resolveConfigPath();
    if (path.isEmpty())
        return;

    QFile f(path);
    if (!f.open(QIODevice::ReadOnly))
        return;

    QJsonParseError err;
    QJsonDocument doc = QJsonDocument::fromJson(f.readAll(), &err);
    if (err.error != QJsonParseError::NoError || !doc.isObject())
        return;

    const QJsonObject root = doc.object();
    const QJsonObject serverObj = root["gesture_server"].toObject();

    host_ = serverObj.value("host").toString(host_);
    port_ = static_cast<quint16>(serverObj.value("port").toInt(port_));
}

QString GestureEngine::resolveConfigPath() const
{
    const QFileInfo info(configFile_);
    if (info.isAbsolute() && info.exists())
        return info.absoluteFilePath();

    const auto searchDir = [this](QDir dir) -> QString {
        for (int i = 0; i < 3; ++i)
        {
            const QString candidate = dir.absoluteFilePath(configFile_);
            if (QFileInfo::exists(candidate))
                return QFileInfo(candidate).absoluteFilePath();
            if (!dir.cdUp())
                break;
        }
        return QString();
    };

    if (const QString fromCwd = searchDir(QDir::current()); !fromCwd.isEmpty())
        return fromCwd;

    if (const QString fromApp =
            searchDir(QDir(QCoreApplication::applicationDirPath()));
        !fromApp.isEmpty())
    {
        return fromApp;
    }

    return QString();
}
