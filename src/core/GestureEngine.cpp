#include "GestureEngine.h"
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QJsonValue>
#include <QDebug>

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

void GestureEngine::start()
{
    emit connectionStatusChanged("Connecting to gesture server...");
    socket_.connectToHost("127.0.0.1", 5555);
}

void GestureEngine::stop()
{
    socket_.disconnectFromHost();
    emit connectionStatusChanged("Disconnected");
}

void GestureEngine::onConnected()
{
    emit connectionStatusChanged("Connected");
}

void GestureEngine::onDisconnected()
{
    emit connectionStatusChanged("Disconnected");
}

void GestureEngine::onError(QAbstractSocket::SocketError)
{
    emit connectionStatusChanged("Connection error");
}

void GestureEngine::onReadyRead()
{
    buffer_.append(QString::fromUtf8(socket_.readAll()));

    while (true)
    {
        int idx = buffer_.indexOf('\n');
        if (idx < 0)
            return;

        QString jsonStr = buffer_.left(idx);
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
        qWarning() << "[C++] JSON parse error:" << err.errorString();
        return;
    }

    if (!doc.isObject())
        return;

    QJsonObject root = doc.object();
    QJsonArray handsArr = root["hands"].toArray();

    QVector<HandInfo> hands;

    for (const QJsonValue &val : handsArr)
    {
        QJsonObject obj = val.toObject();
        HandInfo h;

        h.handedness = obj["handedness"].toString();
        h.visible = obj["visible"].toBool();
        h.gesture = obj["gesture"].toString();
        h.confidence = float(obj["confidence"].toDouble());

        h.pinchDistance = float(obj["pinch_distance"].toDouble());
        h.thumbAngle = float(obj["thumb_angle"].toDouble());

        QJsonArray curlsArr = obj["curls"].toArray();
        for (int i = 0; i < 4 && i < curlsArr.size(); i++)
            h.curls[i] = curlsArr[i].toBool();

        QJsonObject wrist = obj["wrist"].toObject();
        h.wristX = float(wrist["x"].toDouble());
        h.wristY = float(wrist["y"].toDouble());
        h.wristZ = float(wrist["z"].toDouble());

        hands.append(h);
    }

    emit handsUpdated(hands);
}
