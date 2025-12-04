#pragma once

#include <QMainWindow>
#include <QMap>
#include <QListWidget>
#include <QComboBox>
#include <QPushButton>
#include <QLabel>
#include <QCheckBox>
#include <QSystemTrayIcon>
#include <QMenu>
#include <QPointF>

#include "GestureEngine.h"
#include "InputSimulator.h"

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow() override = default;

protected:
    void closeEvent(QCloseEvent *event) override;

private slots:
    void onGestureSelected(QListWidgetItem *item);
    void onBindActionChanged(int index);
    void onTestActionClicked();
    void onTrackingToggled(bool checked);
    void onGestureDetected(const QString &gestureName);
    void onHandsUpdated(const QVector<HandInfo> &hands);
    void onConnectionStatusChanged(const QString &status);

    void onSaveProfile();
    void onLoadProfile();

    void onTrayActivated(QSystemTrayIcon::ActivationReason reason);
    void onTrayShow();
    void onTrayQuit();

private:
    void setupUi();
    void setupConnections();
    void loadDefaultGestures();
    void applyBinding(const QString &gestureName, const QString &actionName);
    const HandInfo *selectPrimaryHand(const QVector<HandInfo> &hands) const;
    void updateCursorFromHand(const HandInfo &hand);
    void resetCursorTracking();

private:
    // UI
    QListWidget *gestureList_ = nullptr;
    QLabel *gestureLabel_ = nullptr;
    QComboBox *actionCombo_ = nullptr;
    QPushButton *testButton_ = nullptr;
    QCheckBox *trackingCheckBox_ = nullptr;
    QLabel *statusLabel_ = nullptr;
    QLabel *connectionLabel_ = nullptr;

    QSystemTrayIcon *trayIcon_ = nullptr;
    QMenu *trayMenu_ = nullptr;

    // Logic
    GestureEngine gestureEngine_;
    InputSimulator inputSim_;

    // gestureName -> actionName
    QMap<QString, QString> gestureBindings_;

    // cursor tracking state
    QPointF cursorFiltered_{0.5, 0.5};
    bool cursorInitialized_ = false;
    double cursorSmoothingFactor_ = 0.35;
};
