#pragma once

#include <QObject>
#include <QTcpSocket>
#include <QVector>

#include "common/Types.h"

class GestureEngine : public QObject
{
    Q_OBJECT

public:
    explicit GestureEngine(QObject *parent = nullptr);

    void start();
    void stop();

    void setEndpoint(const QString &host, quint16 port);
    void setConfigFile(const QString &relativePath);

signals:
    void connectionStatusChanged(const QString &status);
    void handsUpdated(const QVector<HandInfo> &hands);
    void gestureDetected(const QString &gestureName);

private slots:
    void onConnected();
    void onDisconnected();
    void onError(QAbstractSocket::SocketError socketError);
    void onReadyRead();

private:
    void processJson(const QString &jsonStr);
    void loadConfigIfAvailable();
    QString resolveConfigPath() const;

    QTcpSocket socket_;
    QString buffer_;
    QString host_ = QStringLiteral("127.0.0.1");
    quint16 port_ = 5555;
    QString configFile_ = QStringLiteral("config/client_settings.json");
    QString lastGestureEmitted_;
};
