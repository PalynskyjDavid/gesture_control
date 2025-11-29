#include "MainWindow.h"

#include <QWidget>
#include <QGroupBox>
#include <QHBoxLayout>
#include <QVBoxLayout>
#include <QStatusBar>
#include <QSplitter>
#include <QAction>
#include <QMenuBar>
#include <QCloseEvent>

#include <QFileDialog>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QJsonValue>

#include <QApplication>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
{
    setupUi();
    setupConnections();
    loadDefaultGestures();

    // System tray setup
    trayIcon_ = new QSystemTrayIcon(this);
    trayIcon_->setIcon(windowIcon()); // you can set a custom icon later

    trayMenu_ = new QMenu(this);
    QAction *showAct = new QAction(tr("Show"), this);
    QAction *quitAct = new QAction(tr("Quit"), this);

    connect(showAct, &QAction::triggered, this, &MainWindow::onTrayShow);
    connect(quitAct, &QAction::triggered, this, &MainWindow::onTrayQuit);

    trayMenu_->addAction(showAct);
    trayMenu_->addSeparator();
    trayMenu_->addAction(quitAct);

    trayIcon_->setContextMenu(trayMenu_);

    connect(trayIcon_, &QSystemTrayIcon::activated,
            this, &MainWindow::onTrayActivated);

    trayIcon_->show();
}

void MainWindow::setupUi()
{
    auto *central = new QWidget(this);
    auto *mainLayout = new QHBoxLayout(central);

    // Left: gesture list
    auto *gestureGroup = new QGroupBox(tr("Gestures"), central);
    auto *gestureLayout = new QVBoxLayout(gestureGroup);

    gestureList_ = new QListWidget(gestureGroup);
    gestureLayout->addWidget(gestureList_);

    // Right: binding panel
    auto *bindGroup = new QGroupBox(tr("Binding"), central);
    auto *bindLayout = new QVBoxLayout(bindGroup);

    gestureLabel_ = new QLabel(tr("Selected gesture: (none)"), bindGroup);

    actionCombo_ = new QComboBox(bindGroup);
    actionCombo_->addItem("None");
    actionCombo_->addItem("Move mouse (demo)");
    actionCombo_->addItem("Left click");
    actionCombo_->addItem("Right click");
    actionCombo_->addItem("Double click");
    actionCombo_->addItem("Scroll up");
    actionCombo_->addItem("Scroll down");

    testButton_ = new QPushButton(tr("Test action"), bindGroup);
    trackingCheckBox_ = new QCheckBox(tr("Enable tracking (demo)"), bindGroup);

    bindLayout->addWidget(gestureLabel_);
    bindLayout->addWidget(new QLabel(tr("Action:"), bindGroup));
    bindLayout->addWidget(actionCombo_);
    bindLayout->addWidget(testButton_);
    bindLayout->addWidget(trackingCheckBox_);
    bindLayout->addStretch();

    // Splitter so user can resize gesture/binding panels
    auto *splitter = new QSplitter(Qt::Horizontal, central);
    splitter->addWidget(gestureGroup);
    splitter->addWidget(bindGroup);
    splitter->setStretchFactor(0, 1);
    splitter->setStretchFactor(1, 2);

    mainLayout->addWidget(splitter);
    setCentralWidget(central);

    // Menu bar: File → Save profile / Load profile
    auto *fileMenu = menuBar()->addMenu(tr("&File"));
    auto *saveAct = new QAction(tr("Save profile..."), this);
    auto *loadAct = new QAction(tr("Load profile..."), this);
    fileMenu->addAction(saveAct);
    fileMenu->addAction(loadAct);

    connect(saveAct, &QAction::triggered, this, &MainWindow::onSaveProfile);
    connect(loadAct, &QAction::triggered, this, &MainWindow::onLoadProfile);

    statusLabel_ = new QLabel(tr("Ready"), this);
    statusBar()->addWidget(statusLabel_);

    setWindowTitle(tr("Gesture Control (Windows demo)"));
    resize(900, 550);
}

void MainWindow::setupConnections()
{
    connect(gestureList_, &QListWidget::itemClicked,
            this, &MainWindow::onGestureSelected);

    connect(actionCombo_, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &MainWindow::onBindActionChanged);

    connect(testButton_, &QPushButton::clicked,
            this, &MainWindow::onTestActionClicked);

    connect(trackingCheckBox_, &QCheckBox::toggled,
            this, &MainWindow::onTrackingToggled);

    connect(&gestureEngine_, &GestureEngine::gestureDetected,
            this, &MainWindow::onGestureDetected);
}

void MainWindow::loadDefaultGestures()
{
    const QStringList gestures = {
        "open_palm",
        "fist",
        "pinch",
        "swipe_left",
        "swipe_right"};

    for (const auto &g : gestures)
    {
        auto *item = new QListWidgetItem(g, gestureList_);
        item->setData(Qt::UserRole, g);
    }

    if (!gestures.isEmpty())
    {
        gestureList_->setCurrentRow(0);
        gestureLabel_->setText(tr("Selected gesture: %1").arg(gestures.first()));
    }
}

void MainWindow::onGestureSelected(QListWidgetItem *item)
{
    if (!item)
        return;

    const QString gestureName = item->data(Qt::UserRole).toString();
    gestureLabel_->setText(tr("Selected gesture: %1").arg(gestureName));

    const QString currentAction = gestureBindings_.value(gestureName, "None");
    int index = actionCombo_->findText(currentAction);
    if (index < 0)
        index = 0;
    actionCombo_->setCurrentIndex(index);
}

void MainWindow::onBindActionChanged(int index)
{
    auto *item = gestureList_->currentItem();
    if (!item)
        return;

    const QString gestureName = item->data(Qt::UserRole).toString();
    const QString actionName = actionCombo_->itemText(index);
    applyBinding(gestureName, actionName);
}

void MainWindow::applyBinding(const QString &gestureName, const QString &actionName)
{
    gestureBindings_[gestureName] = actionName;
    statusLabel_->setText(
        tr("Bound gesture '%1' to action '%2'")
            .arg(gestureName, actionName));
}

void MainWindow::onTestActionClicked()
{
    auto *item = gestureList_->currentItem();
    if (!item)
        return;

    const QString gestureName = item->data(Qt::UserRole).toString();
    const QString actionName = gestureBindings_.value(gestureName, "None");

    statusLabel_->setText(
        tr("Testing action '%1' for gesture '%2'")
            .arg(actionName, gestureName));

    if (actionName == "Left click")
        inputSim_.leftClick();
    else if (actionName == "Right click")
        inputSim_.rightClick();
    else if (actionName == "Double click")
        inputSim_.doubleClick();
    else if (actionName == "Scroll up")
        inputSim_.scroll(120);
    else if (actionName == "Scroll down")
        inputSim_.scroll(-120);
    else if (actionName == "Move mouse (demo)")
        inputSim_.moveRelative(50, 0);
}

void MainWindow::onTrackingToggled(bool checked)
{
    if (checked)
    {
        gestureEngine_.start();
        statusLabel_->setText(tr("Tracking enabled (demo stub)"));
    }
    else
    {
        gestureEngine_.stop();
        statusLabel_->setText(tr("Tracking disabled"));
    }
}

void MainWindow::onGestureDetected(const QString &gestureName)
{
    const QString actionName = gestureBindings_.value(gestureName, "None");
    if (actionName == "None")
        return;

    statusLabel_->setText(
        tr("Gesture detected: %1 → action: %2")
            .arg(gestureName, actionName));

    if (actionName == "Left click")
        inputSim_.leftClick();
    else if (actionName == "Right click")
        inputSim_.rightClick();
    else if (actionName == "Double click")
        inputSim_.doubleClick();
    else if (actionName == "Scroll up")
        inputSim_.scroll(120);
    else if (actionName == "Scroll down")
        inputSim_.scroll(-120);
    else if (actionName == "Move mouse (demo)")
        inputSim_.moveRelative(20, 0);
}

// ---------- JSON profile save/load ----------

void MainWindow::onSaveProfile()
{
    const QString fileName = QFileDialog::getSaveFileName(
        this, tr("Save gesture profile"), QString(),
        tr("Gesture Profiles (*.json);;All Files (*.*)"));
    if (fileName.isEmpty())
        return;

    QJsonObject root;
    QJsonObject bindingsObj;

    for (auto it = gestureBindings_.cbegin(); it != gestureBindings_.cend(); ++it)
    {
        bindingsObj[it.key()] = it.value();
    }

    root["bindings"] = bindingsObj;

    QJsonDocument doc(root);
    QFile f(fileName);
    if (!f.open(QIODevice::WriteOnly))
    {
        statusLabel_->setText(tr("Failed to save profile"));
        return;
    }
    f.write(doc.toJson());
    f.close();
    statusLabel_->setText(tr("Profile saved to %1").arg(fileName));
}

void MainWindow::onLoadProfile()
{
    const QString fileName = QFileDialog::getOpenFileName(
        this, tr("Load gesture profile"), QString(),
        tr("Gesture Profiles (*.json);;All Files (*.*)"));
    if (fileName.isEmpty())
        return;

    QFile f(fileName);
    if (!f.open(QIODevice::ReadOnly))
    {
        statusLabel_->setText(tr("Failed to open profile"));
        return;
    }
    const QByteArray data = f.readAll();
    f.close();

    QJsonParseError err{};
    QJsonDocument doc = QJsonDocument::fromJson(data, &err);
    if (err.error != QJsonParseError::NoError)
    {
        statusLabel_->setText(tr("Invalid JSON profile"));
        return;
    }

    const QJsonObject root = doc.object();
    const QJsonObject bindingsObj = root["bindings"].toObject();

    gestureBindings_.clear();

    for (auto it = bindingsObj.begin(); it != bindingsObj.end(); ++it)
    {
        gestureBindings_[it.key()] = it.value().toString("None");
    }

    // Refresh current selection
    auto *item = gestureList_->currentItem();
    if (item)
    {
        const QString gestureName = item->data(Qt::UserRole).toString();
        const QString actionName = gestureBindings_.value(gestureName, "None");
        int index = actionCombo_->findText(actionName);
        if (index < 0)
            index = 0;
        actionCombo_->setCurrentIndex(index);
    }

    statusLabel_->setText(tr("Profile loaded from %1").arg(fileName));
}

// ---------- System tray ----------

void MainWindow::closeEvent(QCloseEvent *event)
{
    if (trayIcon_ && trayIcon_->isVisible())
    {
        hide();
        statusLabel_->setText(tr("Application minimized to tray"));
        event->ignore();
    }
    else
    {
        QMainWindow::closeEvent(event);
    }
}

void MainWindow::onTrayActivated(QSystemTrayIcon::ActivationReason reason)
{
    if (reason == QSystemTrayIcon::Trigger)
    { // left-click
        if (isVisible())
            hide();
        else
        {
            showNormal();
            raise();
            activateWindow();
        }
    }
}

void MainWindow::onTrayShow()
{
    showNormal();
    raise();
    activateWindow();
}

void MainWindow::onTrayQuit()
{
    trayIcon_->hide();
    qApp->quit();
}
